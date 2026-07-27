from datetime import datetime

from app.forms.schemas import BaseSchema


class ApplicationSummary(BaseSchema):
    """Safe, summary-only view of a persistent application — never includes
    ownership tokens, answer content, or document contents."""

    id: str
    title: str
    status: str
    form_name: str
    form_origin: str
    export_supported: bool
    progress_percentage: int
    created_at: datetime
    updated_at: datetime
    last_opened_at: datetime | None = None


class ApplicationDetail(ApplicationSummary):
    source_language: str
    user_language: str
    output_language: str
    current_field_position: int
    total_required_fields: int
    document_id: str | None = None


class RenameApplicationRequest(BaseSchema):
    title: str


class ClaimApplicationRequest(BaseSchema):
    session_id: str
    session_token: str
    document_id: str | None = None
    document_token: str | None = None
