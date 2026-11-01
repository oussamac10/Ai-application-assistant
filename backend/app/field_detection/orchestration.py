"""Phase 13 — single orchestration entrypoint for the automatic
upload-to-questions flow.

Composes the existing, unmodified Phase 9/10/11/12 services (document
analysis, OCR, field detection, question generation, session creation) in
one synchronous, idempotent call — mirroring how OCR/field-detection
requests already reuse a "completed" prior result instead of recomputing.
No new background-job infrastructure is introduced (out of scope for this
phase; see .agents/AGENTS.md).

Normal users never see this module's internals: every error raised here
carries only a safe `error_code` (mapped to a translated, plain-language
message on the frontend), matching the rest of the codebase's convention.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import fitz
from sqlalchemy.orm import Session

from app.ai.mock_provider import AIProvider, MockAIProvider
from app.documents.models import SourceDocument
from app.documents.service import SourceDocumentService
from app.field_detection.errors import (
    FieldDetectionError,
    FieldDetectionValidationError,
)
from app.field_detection.providers.base import FieldDetectionProvider
from app.field_detection.service import FieldDetectionService
from app.language.detector import (
    UNDETERMINED,
    DetectedLanguage,
    DocumentLanguageDetector,
)
from app.language.service import DocumentLanguageService
from app.ocr.constants import SUPPORTED_OCR_LANGUAGES
from app.ocr.errors import OCRError, OCRValidationError
from app.ocr.repository import OCRRepository
from app.ocr.service import OCRService
from app.sessions.models import FormSession
from app.sessions.repositories import SessionRepository
from app.sessions.services import (
    ResourceNotFoundError as SessionResourceNotFoundError,
)
from app.sessions.services import (
    StateConflictError as SessionStateConflictError,
)
from app.sessions.services import (
    ValidationError as SessionValidationError,
)
from app.storage import factory as storage_factory
from app.translation.base import TranslationProvider

logger = logging.getLogger(__name__)

# A live or already-completed session blocks recreation (idempotent reuse).
# A cancelled/failed session allows a fresh processing attempt.
_RETRYABLE_SESSION_STATUSES = frozenset({"cancelled", "failed"})

# Processing stages surfaced in PrepareQuestionsResult.stage, matching the
# steps described in docs/phases/phase-13-automatic-upload-to-questions.md.
STAGE_OCR = "ocr"
STAGE_FIELD_DETECTION = "field_detection"
STAGE_QUESTION_GENERATION = "question_generation"

# Safe, generic fallback code for any failure not already carrying its own
# specific error_code — the frontend maps this to one translated message.
_GENERIC_FAILURE_CODE = "document_processing_failed"


@dataclass
class UncertaintyInfo:
    has_uncertain_fields: bool
    uncertain_field_count: int


@dataclass
class PrepareQuestionsResult:
    status: str  # "ready" | "needs_clarification" | "failed"
    document_public_id: str
    session: FormSession | None = None
    ownership_token: str | None = None
    reused_existing_session: bool = False
    uncertainty: UncertaintyInfo | None = None
    error_code: str | None = None
    # Which step failed, when status == "failed" — never shown to the user
    # verbatim; the frontend picks a translated message from error_code.
    # Persisted so a retry can skip already-completed steps (see
    # FieldDetectionService.request_detection's own idempotent reuse).
    stage: str | None = None


class PrepareQuestionsService:
    def __init__(
        self,
        db: Session,
        ai_provider: AIProvider | None = None,
        current_user_id: str | None = None,
        field_detection_provider: FieldDetectionProvider | None = None,
        translation_provider: TranslationProvider | None = None,
        fallback_translation_provider: TranslationProvider | None = None,
        language_detector: DocumentLanguageDetector | None = None,
        trusted_worker: bool = False,
    ):
        self.db = db
        self.ai_provider: AIProvider = (
            ai_provider if ai_provider is not None else MockAIProvider()
        )
        self.current_user_id = current_user_id
        self._trusted_worker = trusted_worker
        self.document_service = SourceDocumentService(db, trusted_worker=trusted_worker)
        self.session_repo = SessionRepository(db)
        self.ocr_repo = OCRRepository()
        # Test-only seam: production callers always leave this None so
        # FieldDetectionService resolves the configured provider itself.
        self._field_detection_provider = field_detection_provider
        # Same seam for translation (Phase 15): production leaves these None
        # and FieldDetectionService resolves the configured providers.
        self._translation_provider = translation_provider
        self._fallback_translation_provider = fallback_translation_provider
        self._language_detector = language_detector

    async def prepare(
        self,
        document_public_id: str,
        ownership_token: str | None,
        user_language: str,
        output_language: str | None = None,
    ) -> PrepareQuestionsResult:
        started = time.perf_counter()
        doc = self.document_service.get_document(
            document_public_id, ownership_token, self.current_user_id
        )

        existing = self.session_repo.get_latest_session_by_source_document_id(doc.id)
        if existing is not None and existing.status not in _RETRYABLE_SESSION_STATUSES:
            # The idempotent path: a retry (frontend re-render, user refresh,
            # a client that gave up on a slow first attempt) reuses the
            # session instead of re-running detection or regenerating any
            # question.
            logger.info(
                "prepare-questions reused existing session: document=%s session=%s "
                "total_duration=%.2fs (no provider or AI calls)",
                document_public_id,
                existing.public_id,
                time.perf_counter() - started,
            )
            return PrepareQuestionsResult(
                status="ready",
                document_public_id=document_public_id,
                session=existing,
                ownership_token=None,
                reused_existing_session=True,
            )

        if doc.matched_template_key:
            # A recognized template declares its own language, so there is
            # nothing to detect; an unspecified output language follows the
            # interface language as before.
            session, token = self.document_service.create_session_from_document(
                document_public_id,
                ownership_token,
                user_language,
                output_language or user_language,
                current_user_id=self.current_user_id,
            )
            return PrepareQuestionsResult(
                status="ready",
                document_public_id=document_public_id,
                session=session,
                ownership_token=token,
            )

        next_step = (doc.analysis_result or {}).get("next_step")
        if next_step not in ("ocr_required", "dynamic_field_detection"):
            raise FieldDetectionValidationError(
                "This document could not be processed automatically.",
                "cannot_process_automatically",
            )

        ocr_started = time.perf_counter()
        if next_step == "ocr_required":
            try:
                self._run_ocr(doc, ownership_token, user_language)
            except OCRError as e:
                return self._failed_result(document_public_id, stage=STAGE_OCR, exc=e)
        ocr_duration = time.perf_counter() - ocr_started

        # What language is this document actually in? Answered once, here —
        # after text extraction/OCR and before anything language-sensitive
        # (RTL-aware geometry grouping, question generation, translation).
        # Persisted, so a repeat request reuses it and calls no detector.
        language_started = time.perf_counter()
        detected_language = await self._detect_document_language(doc)
        language_duration = time.perf_counter() - language_started

        # The completed form is written in the *form's* language. With
        # detection in place that is a fact about the document, not a choice
        # the user should have to make, so an unspecified output language
        # resolves to the detected one — falling back to the interface
        # language only when the document's language is undetermined.
        if not output_language:
            output_language = (
                detected_language.language
                if detected_language.is_determined
                else user_language
            )

        field_detection_service = FieldDetectionService(
            self.db,
            provider=self._field_detection_provider,
            ai_provider=self.ai_provider,
            current_user_id=self.current_user_id,
            translation_provider=self._translation_provider,
            fallback_translation_provider=self._fallback_translation_provider,
            trusted_worker=self._trusted_worker,
        )
        detection_started = time.perf_counter()
        try:
            field_detection_service.request_detection(
                document_public_id, ownership_token
            )
        except FieldDetectionError as e:
            return self._failed_result(
                document_public_id, stage=STAGE_FIELD_DETECTION, exc=e
            )

        detection_duration = time.perf_counter() - detection_started

        question_started = time.perf_counter()
        try:
            (
                session,
                token,
            ) = await field_detection_service.create_session_from_confirmed_fields(
                document_public_id,
                ownership_token,
                user_language,
                output_language,
                include_auto_usable=True,
                document_language=detected_language.language,
            )
        except FieldDetectionValidationError as e:
            if e.error_code == "field_detection_invalid_result":
                return self._no_usable_questions_result(
                    document_public_id, field_detection_service, ownership_token
                )
            return self._failed_result(
                document_public_id, stage=STAGE_QUESTION_GENERATION, exc=e
            )
        except (
            SessionValidationError,
            SessionResourceNotFoundError,
            SessionStateConflictError,
        ) as e:
            # A field-content or version-level problem already surfaces as
            # FieldDetectionValidationError above; this catches a failure
            # from the *session-creation* step itself (e.g. a language/
            # state mismatch) — same safe treatment, never a raw 4xx/5xx
            # with no error_code reaching the client.
            return self._failed_result(
                document_public_id, stage=STAGE_QUESTION_GENERATION, exc=e
            )

        question_duration = time.perf_counter() - question_started

        result = field_detection_service.get_detection_result(
            document_public_id, ownership_token
        )
        clarification_count = sum(
            1 for f in result.fields if f.review_status == "needs_clarification"
        )
        uncertainty = (
            UncertaintyInfo(
                has_uncertain_fields=True, uncertain_field_count=clarification_count
            )
            if clarification_count > 0
            else None
        )

        # One line per request with the whole cost breakdown, so a slow
        # request can be attributed to a stage without a profiler. Counts and
        # durations only — no document text, labels, or answers.
        # `detection_duration` covers the provider call (Azure or local) plus
        # candidate normalization; `question_resolution_duration` covers
        # translation, field creation, publish and session creation, and the
        # translation share of it is logged by question_bridge.
        logger.info(
            "prepare-questions timing: document=%s ocr_duration=%.2fs "
            "language_duration=%.2fs source_language=%s "
            "detection_duration=%.2fs question_resolution_duration=%.2fs "
            "total_duration=%.2fs status=ready questions=%d",
            document_public_id,
            ocr_duration,
            language_duration,
            detected_language.language,
            detection_duration,
            question_duration,
            time.perf_counter() - started,
            len(session.version.fields) if session.version else 0,
        )

        return PrepareQuestionsResult(
            status="ready",
            document_public_id=document_public_id,
            session=session,
            ownership_token=token,
            uncertainty=uncertainty,
        )

    async def _detect_document_language(self, doc: SourceDocument) -> DetectedLanguage:
        """Detects (or reuses) the document's language.

        Failure is non-fatal: a document whose language cannot be determined
        still produces questions, it just carries `und` and lets the
        translation provider detect per batch. Blocking a whole upload because
        a language guess failed would be the wrong trade.
        """
        service = DocumentLanguageService(self.db, self._language_detector)
        try:
            return await service.ensure_detected(doc, *self._language_sources(doc))
        except Exception:
            logger.warning(
                "Document language detection failed for document=%s; continuing "
                "with an undetermined language",
                doc.public_id,
            )
            return DetectedLanguage(UNDETERMINED, 0.0, "unavailable")

    def _language_sources(self, doc: SourceDocument) -> tuple[str, ...]:
        """Text to detect from, most language-bearing first: the document's own
        native text, then OCR output for a scanned document."""
        sources: list[str] = []
        try:
            storage_provider = storage_factory.get_storage_provider()
            with storage_provider.local_path(doc.storage_path) as local_pdf_path:
                with fitz.open(local_pdf_path) as pdf:
                    sources.append(
                        "\n".join(
                            pdf.load_page(index).get_text()
                            for index in range(pdf.page_count)
                        )
                    )
        except Exception:
            logger.info(
                "Could not read native text for language detection (document=%s)",
                doc.public_id,
            )

        ocr_result = self.ocr_repo.get_by_source_document_id(self.db, doc.id)
        if ocr_result is not None and ocr_result.pages:
            sources.append(
                "\n".join(page.text for page in ocr_result.pages if page.text)
            )
        return tuple(sources)

    def _no_usable_questions_result(
        self,
        document_public_id: str,
        field_detection_service: FieldDetectionService,
        ownership_token: str | None,
    ) -> PrepareQuestionsResult:
        result = field_detection_service.get_detection_result(
            document_public_id, ownership_token
        )
        clarification_count = sum(
            1 for f in result.fields if f.review_status == "needs_clarification"
        )
        return PrepareQuestionsResult(
            status="needs_clarification",
            document_public_id=document_public_id,
            uncertainty=UncertaintyInfo(
                has_uncertain_fields=True,
                uncertain_field_count=clarification_count or len(result.fields),
            ),
            error_code="no_usable_questions",
        )

    def _failed_result(
        self,
        document_public_id: str,
        *,
        stage: str,
        exc: Exception,
    ) -> PrepareQuestionsResult:
        """Converts any processing failure at a given stage into a safe,
        structured result instead of letting the exception propagate as a
        raw/unmapped HTTP error. Logs the exception type and stage only —
        never document text, field labels, or answer content. The uploaded
        document itself is untouched (nothing deletes it), so the user can
        simply retry; a retry re-enters `prepare()` and each already-
        completed step (OCR, detection) is reused via its own existing
        idempotent "completed" check rather than rerun.
        """
        logger.error(
            "Automatic processing failed at stage=%s (document=%s): %s",
            stage,
            document_public_id,
            type(exc).__name__,
        )
        return PrepareQuestionsResult(
            status="failed",
            document_public_id=document_public_id,
            error_code=_GENERIC_FAILURE_CODE,
            stage=stage,
        )

    def _run_ocr(
        self, doc: SourceDocument, ownership_token: str | None, user_language: str
    ) -> None:
        # Phase S1-03: OCR script recognition is a property of the scanned
        # document, never of userLanguage (which is the UI/question language).
        ocr_language = "auto" if "auto" in SUPPORTED_OCR_LANGUAGES else "en"
        ocr_service = OCRService(
            self.db,
            current_user_id=self.current_user_id,
            trusted_worker=self._trusted_worker,
        )
        try:
            ocr_service.request_ocr(doc.public_id, ownership_token, ocr_language)
        except OCRValidationError as e:
            if e.error_code == "ocr_not_required":
                # Already ran / not needed by the time we got here — safe to
                # continue into field detection, which reads the OCR result.
                return
            raise
