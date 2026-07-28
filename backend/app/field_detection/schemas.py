from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.field_detection.models import DetectedField, FieldDetectionResult


class BoundingBoxSchema(BaseModel):
    x: float
    y: float
    width: float
    height: float


class DetectedFieldOptionSchema(BaseModel):
    value: str
    position: int


class DetectedFieldSchema(BaseModel):
    fieldId: str = Field(..., serialization_alias="fieldId")
    pageNumber: int = Field(..., serialization_alias="pageNumber")
    label: str
    normalizedName: str = Field(..., serialization_alias="normalizedName")
    fieldType: str = Field(..., serialization_alias="fieldType")
    required: bool | None = None
    multiple: bool
    confidence: float
    source: str
    labelBoundingBox: BoundingBoxSchema | None = Field(
        None, serialization_alias="labelBoundingBox"
    )
    inputBoundingBox: BoundingBoxSchema | None = Field(
        None, serialization_alias="inputBoundingBox"
    )
    options: list[DetectedFieldOptionSchema] = Field(default_factory=list)
    existingValue: str | None = Field(None, serialization_alias="existingValue")
    reviewStatus: str = Field(..., serialization_alias="reviewStatus")

    class Config:
        populate_by_name = True


class FieldDetectionResultResponse(BaseModel):
    documentId: str = Field(..., serialization_alias="documentId")
    status: str
    provider: str | None = None
    sourceType: str | None = Field(None, serialization_alias="sourceType")
    fieldCount: int | None = Field(None, serialization_alias="fieldCount")
    averageConfidence: float | None = Field(
        None, serialization_alias="averageConfidence"
    )
    fields: list[DetectedFieldSchema] = Field(default_factory=list)
    errorCode: str | None = Field(None, serialization_alias="errorCode")
    expiresAt: datetime = Field(..., serialization_alias="expiresAt")

    class Config:
        populate_by_name = True


class DetectedFieldUpdateRequest(BaseModel):
    label: str | None = None
    normalizedName: str | None = Field(None, alias="normalizedName")
    fieldType: str | None = Field(None, alias="fieldType")
    required: bool | None = None
    inputBoundingBox: BoundingBoxSchema | None = Field(None, alias="inputBoundingBox")
    options: list[str] | None = None
    reviewStatus: str | None = Field(None, alias="reviewStatus")

    class Config:
        populate_by_name = True


def build_detected_field_schema(field: "DetectedField") -> DetectedFieldSchema:
    return DetectedFieldSchema(
        fieldId=field.public_id,
        pageNumber=field.page_number,
        label=field.label,
        normalizedName=field.normalized_name,
        fieldType=field.field_type,
        required=field.required,
        multiple=field.multiple,
        confidence=field.confidence,
        source=field.source,
        labelBoundingBox=(
            BoundingBoxSchema(**field.label_bounding_box)
            if field.label_bounding_box
            else None
        ),
        inputBoundingBox=(
            BoundingBoxSchema(**field.input_bounding_box)
            if field.input_bounding_box
            else None
        ),
        options=[
            DetectedFieldOptionSchema(value=o.value, position=o.position)
            for o in field.options
        ],
        existingValue=field.existing_value,
        reviewStatus=field.review_status,
    )


class UncertaintyInfoSchema(BaseModel):
    hasUncertainFields: bool = Field(..., serialization_alias="hasUncertainFields")
    uncertainFieldCount: int = Field(..., serialization_alias="uncertainFieldCount")

    class Config:
        populate_by_name = True


class PrepareQuestionsResponse(BaseModel):
    """Plain-language-safe response for the automatic upload-to-questions
    orchestration endpoint. Deliberately excludes confidence numbers,
    provider names, field keys, and any other technical detail — see
    docs/claude/domain-rules.md and docs/security.md."""

    documentId: str = Field(..., serialization_alias="documentId")
    status: str  # "ready" | "needs_clarification" | "failed"
    sessionId: str | None = Field(None, serialization_alias="sessionId")
    ownershipToken: str | None = Field(None, serialization_alias="ownershipToken")
    reusedExistingSession: bool = Field(
        False, serialization_alias="reusedExistingSession"
    )
    uncertainty: UncertaintyInfoSchema | None = None
    # Populated only when status == "failed" — a stable machine-readable
    # code the frontend maps to one translated message, and which
    # processing step failed. Never a raw exception message.
    errorCode: str | None = Field(None, serialization_alias="errorCode")
    stage: str | None = None

    class Config:
        populate_by_name = True


def build_field_detection_response(
    document_public_id: str, result: "FieldDetectionResult"
) -> FieldDetectionResultResponse:
    fields = [build_detected_field_schema(field) for field in result.fields]

    return FieldDetectionResultResponse(
        documentId=document_public_id,
        status=result.status,
        provider=result.provider_name,
        sourceType=result.source_type,
        fieldCount=result.field_count,
        averageConfidence=result.average_confidence,
        fields=fields,
        errorCode=result.error_code,
        expiresAt=result.expires_at,
    )
