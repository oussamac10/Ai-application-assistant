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

    @computed_field
    def session_id(self) -> str:
        return self.public_id

    @computed_field
    def progress_percentage(self) -> int:
        if self.total_required_fields <= 0:
            return 0
        val = (self.current_field_position / self.total_required_fields) * 100
        return int(val)


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
