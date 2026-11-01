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
    # There is deliberately no fallback position: `.agents/AGENTS.md`
    # forbids coordinate guessing, and a signature placed in the wrong part of
    # an official form is worse than one the export refuses to place at all.
    #
    # `page` is **one-based**, matching `page_number` everywhere else in the
    # codebase and what a person reads off a printed form. Coordinates are PDF
    # points with a **top-left origin**, the convention PyMuPDF uses and the
    # same one the capture canvas uses — so no flip is applied anywhere.
    page: int = 1
    signature_rect: list[float] | None = Field(None, alias="signatureRect")

    @field_validator("signature_rect", mode="before")
    @classmethod
    def coerce_signature_rect(cls, val: object) -> object:
        """Accepts either `[x, y, w, h]` or `{"x":…, "y":…, "width":…,
        "height":…}`.

        The object form is far easier to read and to review in a committed
        mapping file, where a wrong number puts a signature in the wrong place
        on an official document. The list form is what the renderer consumes.
        """
        if isinstance(val, dict):
            try:
                return [
                    float(val["x"]),
                    float(val["y"]),
                    float(val["width"]),
                    float(val["height"]),
                ]
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(
                    "signatureRect must provide numeric x, y, width and height."
                ) from exc
        return val

    @field_validator("signature_rect")
    @classmethod
    def validate_signature_rect(cls, val: list[float] | None) -> list[float] | None:
        """Rejects a rectangle that cannot hold a signature.

        Caught at template *load* time rather than at export time: a broken
        mapping is a deployment mistake, and finding it when someone tries to
        download their completed form is the worst possible moment.
        """
        if val is None:
            return None
        if len(val) != 4:
            raise ValueError("signatureRect must have exactly x, y, width, height.")
        x, y, width, height = val
        if width <= 0 or height <= 0:
            raise ValueError("signatureRect width and height must be positive.")
        if x < 0 or y < 0:
            raise ValueError("signatureRect must not start off the page.")
        return list(val)

    @field_validator("page")
    @classmethod
    def validate_page(cls, val: int) -> int:
        # One-based. Page 0 is a zero-based mapping written by mistake, and
        # silently accepting it would put the signature on the wrong page.
        if val < 1:
            raise ValueError("page is one-based and must be 1 or greater.")
        return val

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
