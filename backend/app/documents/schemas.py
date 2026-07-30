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
    matchedTemplate: dict[str, Any] | None = Field(
        ..., serialization_alias="matchedTemplate"
    )
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
    # Optional since Phase 15. The completed form has to be written in the
    # language the form itself is in, and that language is now detected from
    # the document rather than chosen by the user — so the upload flow stops
    # asking. A caller may still pin it explicitly (the manual template flow
    # does, where a template genuinely supports several output languages).
    outputLanguage: str | None = Field(default=None, alias="outputLanguage")

    class Config:
        populate_by_name = True
