from datetime import datetime

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


class UserResponse(BaseSchema):
    id: str
    email: str
    created_at: datetime
    last_login_at: datetime | None = None


class AuthErrorDetail(BaseSchema):
    detail: str
    error_code: str | None = Field(default=None)
