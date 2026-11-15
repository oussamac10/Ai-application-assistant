from datetime import datetime

from pydantic import Field, computed_field

from app.forms.schemas import BaseSchema


class SessionCreate(BaseSchema):
    user_language: str
    output_language: str


class SessionResponse(BaseSchema):
    public_id: str
    form_version_id: str
    status: str
    source_language: str
    user_language: str
    output_language: str
    current_field_position: int
    total_required_fields: int
    expires_at: datetime
    created_at: datetime
    form_origin: str
    export_supported: bool
    progress_percentage: int = 0
    form_title: str | None = None
    form_description: str | None = None
    required_documents: list[str] = Field(default_factory=list)
    submission_method: str = "print_and_sign"
    instructions: str | None = None
    is_sponsored_case: bool = False
    organization_name: str | None = None

    @computed_field
    def session_id(self) -> str:
        return self.public_id


class SessionCreateResponse(BaseSchema):
    public_id: str
    ownership_token: str
    status: str
    source_language: str
    user_language: str
    output_language: str
    current_field_position: int
    total_required_fields: int
    expires_at: datetime

    @computed_field
    def session_id(self) -> str:
        return self.public_id
