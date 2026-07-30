import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.ai.mock_provider import AIProvider, MockAIProvider
from app.core.config import settings
from app.documents.models import SourceDocument
from app.documents.service import SourceDocumentService
from app.field_detection.confidence import decide_auto_review_status
from app.field_detection.constants import FIELD_TYPES, REVIEW_STATUSES
from app.field_detection.errors import (
    AzureDocumentIntelligenceError,
    FieldDetectionAlreadyProcessingError,
    FieldDetectionNotFoundError,
    FieldDetectionValidationError,
)
from app.field_detection.extraction import (
    extract_native_document_input,
    extract_ocr_document_input,
)
from app.field_detection.models import (
    DetectedField,
    DetectedFieldOption,
    FieldDetectionResult,
)
from app.field_detection.providers.base import (
    BoundingBox,
    DetectedFieldCandidate,
    DetectionResult,
    FieldDetectionProvider,
)
from app.field_detection.providers.mock import MockFieldDetectionProvider
from app.field_detection.question_bridge import (
    build_review_metadata,
    create_session_from_confirmed_fields,
)
from app.field_detection.repository import FieldDetectionRepository
from app.field_detection.usage import record_provider_usage
from app.ocr.models import OCRResult
from app.ocr.repository import OCRRepository
from app.sessions.models import FormSession

logger = logging.getLogger(__name__)

# Providers that call a paid/remote service, and so are worth recording
# usage (and cache hits) for. The local/mock providers cost nothing.
_METERED_PROVIDERS = frozenset({"azure"})


def _active_model_id() -> str | None:
    """The model identifier that participates in the cache fingerprint.
    Only remote providers have one."""
    if settings.FIELD_DETECTION_PROVIDER == "azure":
        return settings.AZURE_DOCUMENT_INTELLIGENCE_MODEL_ID
    return None


def build_detection_fingerprint(
    *,
    checksum: str,
    provider: str,
    model_id: str | None,
    analysis_version: int,
) -> str:
    """Stable hash identifying "this document, analyzed this way".

    Includes the document's own content checksum, so re-uploading an
    identical file under a new document id still recomputes (the result
    row is per-document) while an unchanged document never re-calls a paid
    provider for the same configuration.
    """
    material = f"{checksum}|{provider}|{model_id or '-'}|{analysis_version}"
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def build_default_provider() -> FieldDetectionProvider:
    if settings.FIELD_DETECTION_PROVIDER == "mock":
        return MockFieldDetectionProvider()
    if settings.FIELD_DETECTION_PROVIDER == "local":
        from app.field_detection.providers.local import LocalFieldDetectionProvider

        return LocalFieldDetectionProvider()
    if settings.FIELD_DETECTION_PROVIDER == "azure":
        # Imported lazily so a local/mock deployment never pays for the
        # Azure module's imports, matching the local provider above.
        from app.field_detection.providers.azure import (
            AzureDocumentIntelligenceProvider,
        )

        return AzureDocumentIntelligenceProvider()
    raise FieldDetectionValidationError(
        f"Unknown field detection provider '{settings.FIELD_DETECTION_PROVIDER}'.",
        "field_detection_not_required",
    )


class FieldDetectionService:
    def __init__(
        self,
        db: Session,
        provider: FieldDetectionProvider | None = None,
        ai_provider: AIProvider | None = None,
        current_user_id: str | None = None,
    ):
        self.db = db
        self.repo = FieldDetectionRepository()
        self.ocr_repo = OCRRepository()
        self.document_service = SourceDocumentService(db)
        self._provider = provider
        self.ai_provider: AIProvider = (
            ai_provider if ai_provider is not None else MockAIProvider()
        )
        # Resolved from the auth cookie, never trusted from the client body
        # — every document lookup below authorizes against this (or, for
        # anonymous callers, the ownership token) via SourceDocumentService,
        # mirroring the dual-ownership model used by sessions/answers/pdf.
        self.current_user_id = current_user_id

    @property
    def provider(self) -> FieldDetectionProvider:
        if self._provider is None:
            self._provider = build_default_provider()
        return self._provider

    def _determine_source(self, doc: SourceDocument) -> tuple[str, OCRResult | None]:
        if doc.matched_template_key:
            raise FieldDetectionValidationError(
                "This document matches a supported template; use the guided workflow instead.",
                "supported_template_detected",
            )

        analysis = doc.analysis_result or {}
        next_step = analysis.get("next_step")

        if next_step == "dynamic_field_detection":
            return "native", None

        if next_step == "ocr_required":
            ocr_result = self.ocr_repo.get_by_source_document_id(self.db, doc.id)
            if ocr_result is None:
                raise FieldDetectionValidationError(
                    "OCR is required before field detection.", "ocr_required"
                )
            if ocr_result.status != "completed":
                raise FieldDetectionValidationError(
                    "OCR must complete before field detection can run.",
                    "ocr_not_complete",
                )
            return "ocr", ocr_result

        raise FieldDetectionValidationError(
            "This document does not require dynamic field detection.",
            "field_detection_not_required",
        )

    def request_detection(
        self, document_public_id: str, ownership_token: str | None
    ) -> FieldDetectionResult:
        doc = self.document_service.get_document(
            document_public_id, ownership_token, self.current_user_id
        )
        source_type, ocr_result = self._determine_source(doc)

        analysis_version = settings.FIELD_DETECTION_ANALYSIS_VERSION
        fingerprint = build_detection_fingerprint(
            checksum=doc.checksum_sha256,
            provider=settings.FIELD_DETECTION_PROVIDER,
            model_id=_active_model_id(),
            analysis_version=analysis_version,
        )
        existing = self.repo.get_by_source_document_and_version(
            self.db, doc.id, analysis_version
        )
        if existing is not None:
            if existing.status == "processing":
                raise FieldDetectionAlreadyProcessingError(
                    "Field detection is already in progress for this document."
                )
            # A completed result is only reused when it came from the same
            # provider/model/version — otherwise a provider switch would
            # serve the previous provider's fields. For a paid provider
            # this reuse is also what stops a retry from being billed
            # twice; the cache hit is recorded as usage with
            # served_from_cache=True and no provider call.
            if existing.status == "completed":
                if existing.detection_fingerprint == fingerprint:
                    self._record_cache_hit(doc, existing)
                    return existing
                logger.info(
                    "Detection configuration changed for document %s; recomputing",
                    doc.public_id,
                )

        now = datetime.now(UTC)
        if existing is None:
            result = FieldDetectionResult(
                source_document_id=doc.id,
                ocr_result_id=ocr_result.id if ocr_result else None,
                status="processing",
                analysis_version=analysis_version,
                source_type=source_type,
                started_at=now,
                expires_at=doc.expires_at,
                created_at=now,
                updated_at=now,
            )
            result = self.repo.create(self.db, result)
        else:
            result = existing
            result.status = "processing"
            result.ocr_result_id = ocr_result.id if ocr_result else None
            result.source_type = source_type
            result.error_code = None
            result.error_message = None
            result.started_at = now
            result.expires_at = doc.expires_at
            result = self.repo.update(self.db, result)

        try:
            if source_type == "native":
                document_input = extract_native_document_input(Path(doc.storage_path))
            else:
                assert ocr_result is not None
                document_input = extract_ocr_document_input(
                    ocr_result, Path(doc.storage_path)
                )

            detection_result = self.provider.detect(document_input)
            fields = [
                self._candidate_to_model(candidate, order)
                for order, candidate in enumerate(detection_result.fields)
            ]

            result.status = "completed"
            result.provider_name = detection_result.provider_name
            result.provider_version = detection_result.provider_version
            result.field_count = len(fields)
            result.average_confidence = (
                sum(c.confidence for c in detection_result.fields)
                / len(detection_result.fields)
                if detection_result.fields
                else 0.0
            )
            result.completed_at = datetime.now(UTC)
            result.detection_fingerprint = fingerprint
            self.repo.replace_fields(self.db, result, fields)
            self._record_provider_success(doc, detection_result)
        except AzureDocumentIntelligenceError as e:
            # A remote-provider failure is recorded (for cost/diagnostics)
            # and then re-raised as the ordinary validation failure the
            # orchestration layer already knows how to turn into a safe,
            # generic user message — the Azure code never reaches the user.
            result.status = "failed"
            result.error_code = e.error_code
            result.error_message = "Field detection processing failed."
            self.repo.update(self.db, result)
            self._record_provider_failure(doc, e)
            logger.error(
                "Azure field detection failed for document %s: code=%s request_id=%s",
                doc.public_id,
                e.error_code,
                e.request_id,
            )
            raise FieldDetectionValidationError(
                "Field detection processing failed.", "field_detection_failed"
            ) from e
        except FieldDetectionValidationError:
            raise
        except Exception as e:
            result.status = "failed"
            result.error_code = "field_detection_failed"
            result.error_message = "Field detection processing failed."
            self.repo.update(self.db, result)
            raise FieldDetectionValidationError(
                "Field detection processing failed.", "field_detection_failed"
            ) from e

        return result

    # ------------------------------------------------------------------
    # Usage / cost metadata (metered providers only)
    # ------------------------------------------------------------------

    def _provider_diagnostics(self) -> object | None:
        """The last call's diagnostics, when the active provider exposes
        them (currently only Azure). Never raises."""
        return getattr(self._provider, "last_diagnostics", None)

    def _record_cache_hit(
        self, doc: SourceDocument, existing: FieldDetectionResult
    ) -> None:
        if settings.FIELD_DETECTION_PROVIDER not in _METERED_PROVIDERS:
            return
        try:
            record_provider_usage(
                self.db,
                provider=settings.FIELD_DETECTION_PROVIDER,
                source_document_id=doc.id,
                model_id=_active_model_id(),
                api_version=settings.AZURE_DOCUMENT_INTELLIGENCE_API_VERSION,
                user_id=self.current_user_id,
                page_count=doc.page_count,
                succeeded=True,
                served_from_cache=True,
            )
        except Exception:
            logger.warning("Could not record provider cache-hit usage", exc_info=False)

    def _record_provider_success(
        self, doc: SourceDocument, detection_result: DetectionResult
    ) -> None:
        if detection_result.provider_name not in _METERED_PROVIDERS:
            return
        diagnostics = self._provider_diagnostics()
        try:
            record_provider_usage(
                self.db,
                provider=detection_result.provider_name,
                source_document_id=doc.id,
                model_id=getattr(diagnostics, "model_id", None),
                api_version=getattr(diagnostics, "api_version", None),
                user_id=self.current_user_id,
                page_count=getattr(diagnostics, "page_count", doc.page_count),
                duration_seconds=getattr(diagnostics, "duration_seconds", None),
                succeeded=True,
                provider_request_id=getattr(diagnostics, "request_id", None),
                served_from_cache=False,
            )
        except Exception:
            logger.warning("Could not record provider usage", exc_info=False)

    def _record_provider_failure(
        self, doc: SourceDocument, error: AzureDocumentIntelligenceError
    ) -> None:
        try:
            record_provider_usage(
                self.db,
                provider=settings.FIELD_DETECTION_PROVIDER,
                source_document_id=doc.id,
                model_id=_active_model_id(),
                api_version=settings.AZURE_DOCUMENT_INTELLIGENCE_API_VERSION,
                user_id=self.current_user_id,
                page_count=doc.page_count,
                succeeded=False,
                error_code=error.error_code,
                provider_request_id=error.request_id,
                served_from_cache=False,
            )
        except Exception:
            logger.warning("Could not record provider failure usage", exc_info=False)

    def get_detection_result(
        self, document_public_id: str, ownership_token: str | None
    ) -> FieldDetectionResult:
        doc = self.document_service.get_document(
            document_public_id, ownership_token, self.current_user_id
        )
        result = self.repo.get_by_source_document_and_version(
            self.db, doc.id, settings.FIELD_DETECTION_ANALYSIS_VERSION
        )
        if result is None:
            raise FieldDetectionNotFoundError(
                "No field-detection result exists for this document yet."
            )
        return result

    async def create_session_from_confirmed_fields(
        self,
        document_public_id: str,
        ownership_token: str | None,
        user_language: str,
        output_language: str,
        include_auto_usable: bool = False,
    ) -> tuple[FormSession, str]:
        doc = self.document_service.get_document(
            document_public_id, ownership_token, self.current_user_id
        )
        result = self.repo.get_by_source_document_and_version(
            self.db, doc.id, settings.FIELD_DETECTION_ANALYSIS_VERSION
        )
        if result is None or result.status != "completed":
            raise FieldDetectionNotFoundError(
                "No completed field-detection result exists for this document."
            )
        session, token = await create_session_from_confirmed_fields(
            self.db,
            doc,
            result,
            user_language,
            output_language,
            self.ai_provider,
            current_user_id=self.current_user_id,
            include_auto_usable=include_auto_usable,
        )
        result.review_metadata = build_review_metadata(result)
        self.repo.update(self.db, result)
        return session, token

    def _resolve_field(
        self, document_public_id: str, ownership_token: str | None, field_public_id: str
    ) -> DetectedField:
        result = self.get_detection_result(document_public_id, ownership_token)
        field = self.repo.get_field_by_public_id(self.db, field_public_id)
        if field is None or field.detection_result_id != result.id:
            raise FieldDetectionNotFoundError(
                "No detected field exists with this id for this document."
            )
        return field

    def update_field(
        self,
        document_public_id: str,
        ownership_token: str | None,
        field_public_id: str,
        *,
        label: str | None = None,
        normalized_name: str | None = None,
        field_type: str | None = None,
        required: bool | None = None,
        input_bounding_box: dict[str, float] | None = None,
        options: list[str] | None = None,
        review_status: str | None = None,
    ) -> DetectedField:
        """Applies a user correction to a candidate field. Only the caller-
        supplied attributes are changed; everything else is left as detected.
        """
        field = self._resolve_field(
            document_public_id, ownership_token, field_public_id
        )

        if field_type is not None:
            if field_type not in FIELD_TYPES:
                raise FieldDetectionValidationError(
                    f"Unknown field_type '{field_type}'.",
                    "field_detection_invalid_result",
                )
            field.field_type = field_type

        if review_status is not None:
            if review_status not in REVIEW_STATUSES:
                raise FieldDetectionValidationError(
                    f"Unknown review_status '{review_status}'.",
                    "field_detection_invalid_result",
                )
            field.review_status = review_status
        elif field.review_status == "pending_review":
            # Any correction the user makes counts as having reviewed it.
            field.review_status = "edited"

        if label is not None:
            field.label = label
        if normalized_name is not None:
            field.normalized_name = normalized_name
        if required is not None:
            field.required = required
        if input_bounding_box is not None:
            field.input_bounding_box = input_bounding_box

        field = self.repo.update_field(self.db, field)

        if options is not None:
            field = self.repo.replace_field_options(self.db, field, options)

        return field

    def reject_field(
        self, document_public_id: str, ownership_token: str | None, field_public_id: str
    ) -> DetectedField:
        """Marks a candidate as rejected rather than deleting it, preserving
        review history."""
        field = self._resolve_field(
            document_public_id, ownership_token, field_public_id
        )
        field.review_status = "rejected"
        return self.repo.update_field(self.db, field)

    def _candidate_to_model(
        self, candidate: DetectedFieldCandidate, display_order: int
    ) -> DetectedField:
        # In "auto" mode, the normal-user upload flow (Phase 13) never shows
        # a manual review step, so review_status must already reflect the
        # deterministic confidence decision at detection time. In "manual"
        # mode every candidate starts "pending_review", preserving the exact
        # Phase 11 admin/debug review-screen behavior.
        if settings.FIELD_DETECTION_REVIEW_MODE == "auto":
            review_status = decide_auto_review_status(candidate)
        else:
            review_status = "pending_review"

        return DetectedField(
            page_number=candidate.page_number,
            display_order=display_order,
            label=candidate.label,
            normalized_name=candidate.normalized_name,
            field_type=candidate.field_type,
            required=candidate.required,
            multiple=candidate.multiple,
            confidence=candidate.confidence,
            source=candidate.source,
            label_bounding_box=_box_to_dict(candidate.label_bounding_box),
            input_bounding_box=_box_to_dict(candidate.input_bounding_box),
            existing_value=candidate.existing_value,
            review_status=review_status,
            options=[
                DetectedFieldOption(value=value, position=position)
                for position, value in enumerate(candidate.options)
            ],
        )


def _box_to_dict(box: BoundingBox | None) -> dict[str, float] | None:
    if box is None:
        return None
    return {"x": box.x, "y": box.y, "width": box.width, "height": box.height}
