from typing import Any

from pydantic import computed_field

from app.forms.schemas import BaseSchema


class AnswerSubmitRequest(BaseSchema):
    original_answer: str


class ClarifySubmitRequest(BaseSchema):
    values: dict[str, Any]


class ClarificationResponse(BaseSchema):
    missing: list[str]
    question_key: str


class AnswerResponse(BaseSchema):
    id: str
    status: str
    requires_clarification: bool
    clarification: ClarificationResponse | None = None
    validation_status: str
    confirmed_by_user: bool
    # None for a skipped question: a deliberate non-answer, not an empty one.
    original_answer: str | None = None
    normalized_value: Any | None = None
    output_value: str | None = None

    @computed_field
    def answer_id(self) -> str:
        return self.id


class ProgressInfo(BaseSchema):
    confirmed_required_fields: int
    total_required_fields: int
    # Every question the user is asked, and how many they have confirmed.
    # `total_required_fields` counts only mandatory ones and drives completion;
    # these two drive the progress the user sees, which must stay meaningful on
    # a form that marks nothing mandatory.
    total_questions: int = 0
    answered_questions: int = 0
    percentage: int


class FieldOptionInfo(BaseSchema):
    value: str
    label: str


class CurrentFieldResponse(BaseSchema):
    id: str
    key: str
    field_type: str
    required: bool
    position: int
    label: str
    help_text: str | None = None
    placeholder: str | None = None
    options: list[FieldOptionInfo] | None = None
    current_answer_status: str | None = None
    progress: ProgressInfo | None = None

    @computed_field
    def field_id(self) -> str:
        return self.id

    @computed_field
    def field_key(self) -> str:
        return self.key


class SummaryFieldAnswer(BaseSchema):
    field_id: str
    field_key: str
    label: str
    required: bool
    original_answer: str | None = None
    normalized_value: Any | None = None
    output_value: str | None = None
    status: str = "unanswered"
    validation_status: str = "not_checked"
    confirmed_by_user: bool = False


class SummaryResponse(BaseSchema):
    fields: list[SummaryFieldAnswer]
