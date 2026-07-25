from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DocumentAnalysisSummary(BaseModel):
    pageCount: int = Field(..., serialization_alias="pageCount")
    documentType: str = Field(..., serialization_alias="documentType")
    hasNativeText: bool = Field(..., serialization_alias="hasNativeText")
    hasAcroForm: bool = Field(..., serialization_alias="hasAcroForm")
    hasEmbeddedImages: bool = Field(..., serialization_alias="hasEmbeddedImages")
    isProbablyScanned: bool = Field(..., serialization_alias="isProbablyScanned")
    matchedTemplate: dict[str, Any] | None = Field(..., serialization_alias="matchedTemplate")
    nextStep: str = Field(..., serialization_alias="nextStep")

    class Config:
        populate_by_name = True


class DocumentUploadResponse(BaseModel):
    documentId: str = Field(..., serialization_alias="documentId")
    ownershipToken: str | None = Field(None, serialization_alias="ownershipToken")
    status: str
    analysis: DocumentAnalysisSummary | None = None
    expiresAt: datetime = Field(..., serialization_alias="expiresAt")

    class Config:
        populate_by_name = True


class DocumentRetrieveResponse(BaseModel):
    documentId: str = Field(..., serialization_alias="documentId")
    status: str
    analysis: DocumentAnalysisSummary | None = None
    expiresAt: datetime = Field(..., serialization_alias="expiresAt")

    class Config:
        populate_by_name = True


class SessionCreateResponse(BaseModel):
    sessionId: str = Field(..., serialization_alias="sessionId")
    ownershipToken: str = Field(..., serialization_alias="ownershipToken")
    status: str = "created"

    class Config:
        populate_by_name = True


class SessionCreateRequest(BaseModel):
    language: str
    outputLanguage: str = Field(..., alias="outputLanguage")

    class Config:
        populate_by_name = True

