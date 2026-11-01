from datetime import datetime

from pydantic import computed_field

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
