from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    billing_plan: str
    allowed_cases_per_month: int
    role: str = "case_manager"
    organization_type: str = "government"
    verification_status: str = "unverified"
    is_verified_government: bool = False
    verification_details: dict[str, Any] | None = None
    description: str | None = None
    logo_storage_path: str | None = None
    cover_image_storage_path: str | None = None
    office_address: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    official_website_url: str | None = None
    supported_languages: list[str] = ["de", "en"]
    created_at: datetime


class OrganizationProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    office_address: str | None = Field(default=None, max_length=500)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=50)
    official_website_url: str | None = Field(default=None, max_length=500)
    supported_languages: list[str] | None = None


class OrganizationVerificationRequest(BaseModel):
    authority_name: str = Field(..., min_length=2, max_length=255)
    registration_id: str = Field(..., min_length=2, max_length=100)
    official_domain: str = Field(..., min_length=3, max_length=255)
    contact_person_title: str = Field(..., min_length=2, max_length=100)
    notes: str | None = None


class OrganizationMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    email: str
    role: str
    created_at: datetime


class OrganizationMemberInvite(BaseModel):
    email: EmailStr
    role: str = Field(
        default="case_manager", pattern="^(admin|form_editor|viewer|case_manager)$"
    )


class OrganizationMemberRoleUpdate(BaseModel):
    role: str = Field(..., pattern="^(admin|form_editor|viewer|case_manager)$")


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


class OrganizationCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    organization_type: str = Field(
        default="government", pattern="^(government|business)$"
    )
    official_website_url: str | None = Field(default=None, max_length=500)
