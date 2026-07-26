from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.field_detection.models import FieldDetectionResult


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


def build_field_detection_response(
    document_public_id: str, result: "FieldDetectionResult"
) -> FieldDetectionResultResponse:
    fields = [
        DetectedFieldSchema(
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
        for field in result.fields
    ]

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
