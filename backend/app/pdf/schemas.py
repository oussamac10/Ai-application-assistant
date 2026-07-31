from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class PDFFieldMapping(BaseModel):
    field_key: str = Field(..., alias="fieldKey")
    pdf_field_name: str = Field(..., alias="pdfFieldName")
    format: str
    max_length: int | None = Field(None, alias="maxLength")
    overflow: Literal["reject", "truncate", "wrap"] = "reject"
    # Signature fields only. A signature is drawn at coordinates rather than
    # written into an AcroForm text field, so it needs an explicit rectangle.
    # There is deliberately no fallback position: `docs/claude/domain-rules.md`
    # forbids coordinate guessing, and a signature placed in the wrong part of
    # an official form is worse than one the export refuses to place at all.
    page: int = 1
    signature_rect: list[float] | None = Field(None, alias="signatureRect")

    model_config = {
        "populate_by_name": True,
    }

    @field_validator("format")
    @classmethod
    def validate_format(cls, val: str) -> str:
        allowed = {
            "text",
            "date",
            "integer",
            "decimal",
            "money",
            "boolean",
            "single_choice",
            "multiple_choice",
            "email",
            "phone",
            "address",
            "country",
            "person_name",
        }
        if val not in allowed:
            raise ValueError(f"Unsupported format '{val}'. Allowed: {sorted(allowed)}")
        return val


class PDFTemplateMapping(BaseModel):
    template_key: str = Field(..., alias="templateKey")
    form_version_key: str = Field(..., alias="formVersionKey")
    mapping_version: int = Field(..., alias="mappingVersion")
    strategy: Literal["acroform"] = "acroform"
    fields: list[PDFFieldMapping]

    model_config = {
        "populate_by_name": True,
    }


class ExportResponse(BaseModel):
    export_id: str = Field(..., alias="exportId")
    status: str
    file_name: str = Field(..., alias="fileName")
    content_type: str = Field(..., alias="contentType")
    file_size: int | None = Field(None, alias="fileSize")
    expires_at: datetime = Field(..., alias="expiresAt")
    download_url: str = Field(..., alias="downloadUrl")

    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }
