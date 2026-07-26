from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.ocr.models import OCRResult


class OCRRequest(BaseModel):
    language: str


class BoundingBoxSchema(BaseModel):
    x: int
    y: int
    width: int
    height: int


class OCRWordSchema(BaseModel):
    text: str
    confidence: float
    boundingBox: BoundingBoxSchema = Field(..., serialization_alias="boundingBox")

    class Config:
        populate_by_name = True


class OCRLineSchema(BaseModel):
    text: str
    confidence: float
    boundingBox: BoundingBoxSchema = Field(..., serialization_alias="boundingBox")
    words: list[OCRWordSchema]

    class Config:
        populate_by_name = True


class OCRPageSchema(BaseModel):
    pageNumber: int = Field(..., serialization_alias="pageNumber")
    width: int
    height: int
    text: str
    averageConfidence: float = Field(..., serialization_alias="averageConfidence")
    lines: list[OCRLineSchema]

    class Config:
        populate_by_name = True


def build_ocr_result_response(
    document_public_id: str, result: "OCRResult"
) -> "OCRResultResponse":
    pages = [
        OCRPageSchema(
            pageNumber=page.page_number,
            width=page.width,
            height=page.height,
            text=page.text,
            averageConfidence=page.average_confidence,
            lines=[
                OCRLineSchema(
                    text=line["text"],
                    confidence=line["confidence"],
                    boundingBox=BoundingBoxSchema(**line["boundingBox"]),
                    words=[
                        OCRWordSchema(
                            text=word["text"],
                            confidence=word["confidence"],
                            boundingBox=BoundingBoxSchema(**word["boundingBox"]),
                        )
                        for word in line["words"]
                    ],
                )
                for line in page.lines
            ],
        )
        for page in result.pages
    ]
    return OCRResultResponse(
        documentId=document_public_id,
        status=result.status,
        provider=result.provider_name,
        language=result.language,
        pageCount=result.page_count,
        pages=pages,
        errorCode=result.error_code,
        expiresAt=result.expires_at,
    )


class OCRResultResponse(BaseModel):
    documentId: str = Field(..., serialization_alias="documentId")
    status: str
    provider: str | None = None
    language: str
    pageCount: int | None = Field(None, serialization_alias="pageCount")
    pages: list[OCRPageSchema] = Field(default_factory=list)
    errorCode: str | None = Field(None, serialization_alias="errorCode")
    expiresAt: datetime = Field(..., serialization_alias="expiresAt")

    class Config:
        populate_by_name = True
