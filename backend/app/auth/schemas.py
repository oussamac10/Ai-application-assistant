from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


class RegisterRequest(BaseSchema):
    email: EmailStr
    password: str
    password_confirmation: str


class LoginRequest(BaseSchema):
    email: EmailStr
    password: str


class TokenConfirmRequest(BaseSchema):
    token: str


class PasswordResetRequest(BaseSchema):
    email: EmailStr


class PasswordResetConfirmRequest(BaseSchema):
    token: str
    password: str
    password_confirmation: str


class ActionStatusResponse(BaseSchema):
    status: str


class UserResponse(BaseSchema):
    id: str
    email: str
    role: str = "user"
    email_verified: bool = False
    email_verified_at: datetime | None = None
    created_at: datetime
    last_login_at: datetime | None = None


class ExportedAccountInfo(BaseSchema):
    id: str
    email: str
    role: str
    email_verified: bool
    email_verified_at: datetime | None = None
    created_at: datetime
    last_login_at: datetime | None = None


class ExportedAnswerItem(BaseSchema):
    field_key: str
    field_type: str
    original_answer: str | None = None
    normalized_value: Any | None = None
    output_value: str | None = None
    status: str
    confirmed_by_user: bool
    confirmed_at: datetime | None = None


class ExportedApplicationItem(BaseSchema):
    id: str
    title: str
    form_name: str
    status: str
    source_language: str
    user_language: str
    output_language: str
    created_at: datetime
    updated_at: datetime
    answers: list[ExportedAnswerItem] = []


class ExportedDocumentItem(BaseSchema):
    id: str
    original_filename: str
    content_type: str
    size_bytes: int
    page_count: int | None = None
    detected_source_language: str | None = None
    created_at: datetime


class ExportedVaultItem(BaseSchema):
    question_key: str
    field_type: str
    value: str
    value_language: str
    updated_at: datetime


class AccountDataExportResponse(BaseSchema):
    exported_at: datetime
    account: ExportedAccountInfo
    profile_vault: list[ExportedVaultItem] = []
    applications: list[ExportedApplicationItem] = []
    documents: list[ExportedDocumentItem] = []


class AuthErrorDetail(BaseSchema):
    detail: str
    error_code: str | None = Field(default=None)
