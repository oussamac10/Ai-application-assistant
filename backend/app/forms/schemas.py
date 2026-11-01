from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


def to_camel(string: str) -> str:
    parts = string.split("_")
    return parts[0] + "".join(word.capitalize() for word in parts[1:])


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


# Translations
class TranslationSchema(BaseSchema):
    language: str
    label: str
    help_text: str | None = None
    placeholder: str | None = None


class OptionTranslationSchema(BaseSchema):
    language: str
    label: str


# Option for Choices
class OptionSchema(BaseSchema):
    id: str | None = None
    value: str
    position: int
    translations: list[OptionTranslationSchema] = Field(default_factory=list)


# Field schemas
class FieldCreate(BaseSchema):
    key: str
    field_type: str
    # `requiredness` is the source of truth; `required` is derived from it (see
    # `resolve_requiredness` in app/forms/services.py). A caller that sets
    # neither gets the historical default — an explicitly declared,
    # hand-authored template field.
    required: bool = True
    requiredness: str | None = None
    position: int
    configuration: dict[str, Any] = Field(default_factory=dict)
    question_key: str | None = None
    translations: list[TranslationSchema] = Field(default_factory=list)
    options: list[OptionSchema] = Field(default_factory=list)


class FieldUpdate(BaseSchema):
    key: str | None = None
    field_type: str | None = None
    required: bool | None = None
    requiredness: str | None = None
    position: int | None = None
    configuration: dict[str, Any] | None = None
    question_key: str | None = None
    translations: list[TranslationSchema] | None = None
    options: list[OptionSchema] | None = None


class FieldResponse(BaseSchema):
    id: str
    key: str
    field_type: str
    required: bool
    requiredness: str = "unknown"
    position: int
    configuration: dict[str, Any]
    question_key: str | None = None
    translations: list[TranslationSchema]
    options: list[OptionSchema]


# Version schemas
class VersionCreate(BaseSchema):
    source_language: str
    supported_output_languages: list[str]


class VersionResponse(BaseSchema):
    id: str
    form_template_id: str
    version_number: int
    status: str
    source_language: str
    supported_output_languages: list[str]
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None
    fields: list[FieldResponse] = Field(default_factory=list)


# Template schemas
class TemplateCreate(BaseSchema):
    key: str
    name: str
    description: str | None = None


class TemplateResponse(BaseSchema):
    id: str
    key: str
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class PublishedFormResponse(BaseSchema):
    id: str
    template_key: str
    name: str
    description: str | None = None
    version_number: int
    source_language: str
    supported_output_languages: list[str]


# Organization Form Management & Review Schemas (Phase G2)
class OrganizationFormSummary(BaseSchema):
    id: str
    key: str
    name: str
    description: str | None = None
    category: str = "general"
    submission_method: str = "print_and_sign"
    instructions: str | None = None
    required_documents: list[str] = Field(default_factory=list)
    active_version_id: str | None = None
    version_number: int = 1
    status: str = "needs_review"
    fields_count: int = 0
    source_pdf_storage_path: str | None = None
    has_pdf: bool = False
    created_at: datetime
    updated_at: datetime


class FormReviewDetailResponse(BaseSchema):
    template_id: str
    version_id: str
    key: str
    name: str
    description: str | None = None
    category: str = "general"
    submission_method: str = "print_and_sign"
    instructions: str | None = None
    required_documents: list[str] = Field(default_factory=list)
    status: str
    version_number: int
    source_language: str = "de"
    source_pdf_storage_path: str | None = None
    review_notes: str | None = None
    page_count: int = 1
    page_dimensions: list[dict[str, Any]] = Field(default_factory=list)
    fields: list[FieldResponse] = Field(default_factory=list)


class FormReviewUpdateRequest(BaseSchema):
    name: str | None = None
    description: str | None = None
    category: str | None = None
    submission_method: str | None = None
    instructions: str | None = None
    required_documents: list[str] | None = None
    review_notes: str | None = None


class FieldReviewItem(BaseSchema):
    id: str | None = None
    key: str
    question_key: str | None = None
    field_type: str = "string"
    requiredness: str = "required"
    position: int
    label: str
    help_text: str | None = None
    placeholder: str | None = None
    options: list[OptionSchema] = Field(default_factory=list)
    configuration: dict[str, Any] = Field(default_factory=dict)
