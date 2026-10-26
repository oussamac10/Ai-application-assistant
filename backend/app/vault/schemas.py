from datetime import datetime
from typing import Any

from app.forms.schemas import BaseSchema


class ProfileVaultUpsertRequest(BaseSchema):
    value: str
    field_type: str = "string"
    value_language: str = "en"


class ProfileVaultEntryResponse(BaseSchema):
    question_key: str
    field_type: str
    value: str
    normalized_value: Any | None = None
    value_language: str
    updated_at: datetime


class SaveSessionToVaultResponse(BaseSchema):
    saved_count: int
    saved_keys: list[str]


class PrefillSessionFromVaultResponse(BaseSchema):
    prefilled_count: int
    prefilled_field_keys: list[str]
