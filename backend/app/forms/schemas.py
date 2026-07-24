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
    required: bool = True
    position: int
    configuration: dict[str, Any] = Field(default_factory=dict)
    translations: list[TranslationSchema] = Field(default_factory=list)
    options: list[OptionSchema] = Field(default_factory=list)


class FieldUpdate(BaseSchema):
    key: str | None = None
    field_type: str | None = None
    required: bool | None = None
    position: int | None = None
    configuration: dict[str, Any] | None = None
    translations: list[TranslationSchema] | None = None
    options: list[OptionSchema] | None = None


class FieldResponse(BaseSchema):
    id: str
    key: str
    field_type: str
    required: bool
    position: int
    configuration: dict[str, Any]
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
