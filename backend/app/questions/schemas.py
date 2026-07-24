from datetime import datetime

from pydantic import Field

from app.forms.schemas import BaseSchema


class ResolvedQuestion(BaseSchema):
    text: str
    help_text: str | None = Field(default=None, alias="helpText")
    placeholder: str | None = Field(default=None, alias="placeholder")
    source: str
    review_status: str = Field(default="approved", alias="reviewStatus")
    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = Field(default=None, alias="promptVersion")


class QuestionTranslationResponse(BaseSchema):
    id: str
    question_definition_id: str
    language: str
    text: str
    help_text: str | None = None
    placeholder: str | None = None
    source: str
    review_status: str
    provider: str | None = None
    model: str | None = None
    prompt_version: str | None = None
    created_at: datetime
    updated_at: datetime
    approved_at: datetime | None = None


class QuestionDefinitionResponse(BaseSchema):
    id: str
    question_key: str
    field_type: str
    purpose: str
    domain: str | None = None
    version: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    translations: list[QuestionTranslationResponse] = Field(default_factory=list)


class QuestionTranslationCreate(BaseSchema):
    text: str
    help_text: str | None = None
    placeholder: str | None = None
