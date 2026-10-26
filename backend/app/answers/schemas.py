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


class FieldExplanationInfo(BaseSchema):
    summary: str
    where_to_find: str
    example: str


class CurrentFieldResponse(BaseSchema):
    id: str
    key: str
    field_type: str
    required: bool
    # "required" | "optional" | "unknown". `required` is the legacy boolean and
    # cannot express "the document said nothing"; the frontend shows a
    # requiredness label only for the two states that are actually a finding.
    requiredness: str = "unknown"
    # Signature fields only. `signature_requirement` reports what the
    # *document* said; `digital_signature_required` is always False, because a
    # required signature box means the form must be signed before it counts,
    # never that it must be signed electronically inside this application.
    signature_requirement: str | None = None
    digital_signature_required: bool = False
    position: int
    label: str
    help_text: str | None = None
    placeholder: str | None = None
    options: list[FieldOptionInfo] | None = None
    field_explanation: FieldExplanationInfo | None = None
    current_answer_id: str | None = None
    current_answer_status: str | None = None
    original_answer: str | None = None
    normalized_value: Any = None
    output_value: str | None = None
    all_field_keys: list[str] = []
    progress: ProgressInfo | None = None
    page_number: int | None = None
    page_width_pt: float | None = None
    page_height_pt: float | None = None
    input_bounding_box: dict[str, float] | None = None
    source_document_filename: str | None = None
    source_document_page_count: int | None = None

    @computed_field
    def field_id(self) -> str:
        return self.id

    @computed_field
    def field_key(self) -> str:
        return self.key


class SummaryFieldAnswer(BaseSchema):
    field_id: str
    field_key: str
    field_type: str | None = None
    label: str
    source_label: str | None = None
    required: bool
    requiredness: str = "unknown"
    original_answer: str | None = None
    normalized_value: Any | None = None
    output_value: str | None = None
    status: str = "unanswered"
    # "unreached" | "unanswered" | "skipped" | "answered" | "invalid".
    # What the user did, independent of what the document demanded — the
    # summary must tell a deliberate skip from a question never reached, and a
    # signature deferred to the printed form from both.
    answer_state: str = "unreached"
    signature_requirement: str | None = None
    validation_status: str = "not_checked"
    confirmed_by_user: bool = False


class SubmissionChecklistItem(BaseSchema):
    id: str
    title: str
    description: str
    category: str
    required: bool = True


class ConsistencyWarningItem(BaseSchema):
    code: str
    severity: str = "warning"
    field_keys: list[str]
    message: str


class SummaryResponse(BaseSchema):
    fields: list[SummaryFieldAnswer]
    submission_checklist: list[SubmissionChecklistItem] = []
    consistency_warnings: list[ConsistencyWarningItem] = []
    source_language: str | None = None
    user_language: str | None = None
    output_language: str | None = None
    export_supported: bool = False


class ReopenFieldResponse(BaseSchema):
    field_id: str
    position: int
