from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.documents.models import SourceDocument
from app.documents.service import SourceDocumentService
from app.field_detection.constants import FIELD_TYPES, REVIEW_STATUSES
from app.field_detection.errors import (
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
    FieldDetectionProvider,
)
from app.field_detection.providers.mock import MockFieldDetectionProvider
from app.field_detection.repository import FieldDetectionRepository
from app.ocr.models import OCRResult
from app.ocr.repository import OCRRepository


def build_default_provider() -> FieldDetectionProvider:
    if settings.FIELD_DETECTION_PROVIDER == "mock":
        return MockFieldDetectionProvider()
    if settings.FIELD_DETECTION_PROVIDER == "local":
        from app.field_detection.providers.local import LocalFieldDetectionProvider

        return LocalFieldDetectionProvider()
    raise FieldDetectionValidationError(
        f"Unknown field detection provider '{settings.FIELD_DETECTION_PROVIDER}'.",
        "field_detection_not_required",
    )


class FieldDetectionService:
    def __init__(self, db: Session, provider: FieldDetectionProvider | None = None):
        self.db = db
        self.repo = FieldDetectionRepository()
        self.ocr_repo = OCRRepository()
        self.document_service = SourceDocumentService(db)
        self._provider = provider

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
        self, document_public_id: str, ownership_token: str
    ) -> FieldDetectionResult:
        doc = self.document_service.get_document(document_public_id, ownership_token)
        source_type, ocr_result = self._determine_source(doc)

        analysis_version = settings.FIELD_DETECTION_ANALYSIS_VERSION
        existing = self.repo.get_by_source_document_and_version(
            self.db, doc.id, analysis_version
        )
        if existing is not None:
            if existing.status == "processing":
                raise FieldDetectionAlreadyProcessingError(
                    "Field detection is already in progress for this document."
                )
            if existing.status == "completed":
                return existing

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
                document_input = extract_ocr_document_input(ocr_result)

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
            self.repo.replace_fields(self.db, result, fields)
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

    def get_detection_result(
        self, document_public_id: str, ownership_token: str
    ) -> FieldDetectionResult:
        doc = self.document_service.get_document(document_public_id, ownership_token)
        result = self.repo.get_by_source_document_and_version(
            self.db, doc.id, settings.FIELD_DETECTION_ANALYSIS_VERSION
        )
        if result is None:
            raise FieldDetectionNotFoundError(
                "No field-detection result exists for this document yet."
            )
        return result

    def _resolve_field(
        self, document_public_id: str, ownership_token: str, field_public_id: str
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
        ownership_token: str,
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
        self, document_public_id: str, ownership_token: str, field_public_id: str
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
            review_status="pending_review",
            options=[
                DetectedFieldOption(value=value, position=position)
                for position, value in enumerate(candidate.options)
            ],
        )


def _box_to_dict(box: BoundingBox | None) -> dict[str, float] | None:
    if box is None:
        return None
    return {"x": box.x, "y": box.y, "width": box.width, "height": box.height}
