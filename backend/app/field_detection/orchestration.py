"""Phase 13 — single orchestration entrypoint for the automatic
upload-to-questions flow.

Composes the existing, unmodified Phase 9/10/11/12 services (document
analysis, OCR, field detection, question generation, session creation) in
one synchronous, idempotent call — mirroring how OCR/field-detection
requests already reuse a "completed" prior result instead of recomputing.
No new background-job infrastructure is introduced (out of scope for this
phase; see docs/claude/current-phase.md).

Normal users never see this module's internals: every error raised here
carries only a safe `error_code` (mapped to a translated, plain-language
message on the frontend), matching the rest of the codebase's convention.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.ai.mock_provider import AIProvider
from app.documents.models import SourceDocument
from app.documents.service import SourceDocumentService
from app.field_detection.errors import (
    FieldDetectionError,
    FieldDetectionValidationError,
)
from app.field_detection.providers.base import FieldDetectionProvider
from app.field_detection.service import FieldDetectionService
from app.ocr.constants import SUPPORTED_OCR_LANGUAGES
from app.ocr.errors import OCRError, OCRValidationError
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
        ai_provider: AIProvider,
        current_user_id: str | None = None,
        field_detection_provider: FieldDetectionProvider | None = None,
    ):
        self.db = db
        self.ai_provider = ai_provider
        self.current_user_id = current_user_id
        self.document_service = SourceDocumentService(db)
        self.session_repo = SessionRepository(db)
        # Test-only seam: production callers always leave this None so
        # FieldDetectionService resolves the configured provider itself.
        self._field_detection_provider = field_detection_provider

    async def prepare(
        self,
        document_public_id: str,
        ownership_token: str | None,
        user_language: str,
        output_language: str,
    ) -> PrepareQuestionsResult:
        doc = self.document_service.get_document(
            document_public_id, ownership_token, self.current_user_id
        )

        existing = self.session_repo.get_latest_session_by_source_document_id(doc.id)
        if existing is not None and existing.status not in _RETRYABLE_SESSION_STATUSES:
            return PrepareQuestionsResult(
                status="ready",
                document_public_id=document_public_id,
                session=existing,
                ownership_token=None,
                reused_existing_session=True,
            )

        if doc.matched_template_key:
            session, token = self.document_service.create_session_from_document(
                document_public_id,
                ownership_token,
                user_language,
                output_language,
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

        if next_step == "ocr_required":
            try:
                self._run_ocr(doc, ownership_token, user_language)
            except OCRError as e:
                return self._failed_result(document_public_id, stage=STAGE_OCR, exc=e)

        field_detection_service = FieldDetectionService(
            self.db,
            provider=self._field_detection_provider,
            ai_provider=self.ai_provider,
            current_user_id=self.current_user_id,
        )
        try:
            field_detection_service.request_detection(
                document_public_id, ownership_token
            )
        except FieldDetectionError as e:
            return self._failed_result(
                document_public_id, stage=STAGE_FIELD_DETECTION, exc=e
            )

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

        return PrepareQuestionsResult(
            status="ready",
            document_public_id=document_public_id,
            session=session,
            ownership_token=token,
            uncertainty=uncertainty,
        )

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
        ocr_language = (
            user_language if user_language in SUPPORTED_OCR_LANGUAGES else "en"
        )
        ocr_service = OCRService(self.db, current_user_id=self.current_user_id)
        try:
            ocr_service.request_ocr(doc.public_id, ownership_token, ocr_language)
        except OCRValidationError as e:
            if e.error_code == "ocr_not_required":
                # Already ran / not needed by the time we got here — safe to
                # continue into field detection, which reads the OCR result.
                return
            raise
