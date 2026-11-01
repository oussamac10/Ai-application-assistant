from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    billing_plan: str
    allowed_cases_per_month: int
    role: str = "case_manager"
    created_at: datetime


class CaseCreateRequest(BaseModel):
    candidate_name: str = Field(..., min_length=2, max_length=255)
    candidate_email: EmailStr
    form_version_id: str
    user_language: str = Field(default="en", max_length=10)
    notes: str | None = None


class CaseUpdateRequest(BaseModel):
    status: str | None = Field(
        default=None, pattern="^(invited|in_progress|awaiting_review|completed)$"
    )
    notes: str | None = None


class CaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    public_id: str
    organization_id: str
    candidate_name: str
    candidate_email: str
    status: str
    form_version_id: str
    form_title: str | None = None
    form_session_id: str | None = None
    session_public_id: str | None = None
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    invite_token: str | None = None
    total_fields: int = 0
    answered_fields: int = 0
    progress_percent: int = 0


class CandidateInviteRedemptionResponse(BaseModel):
    session_id: str
    session_token: str
    case_public_id: str
    candidate_name: str
    candidate_email: str
    form_title: str
    form_version_id: str
    user_language: str
    source_language: str
    status: str
