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
    ui_theme_config: dict[str, Any] | None = None
    created_at: datetime


class OrganizationProfileUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    description: str | None = None
    office_address: str | None = Field(default=None, max_length=500)
    contact_email: EmailStr | None = None
    contact_phone: str | None = Field(default=None, max_length=50)
    official_website_url: str | None = Field(default=None, max_length=500)
    supported_languages: list[str] | None = None
    ui_theme_config: dict[str, Any] | None = None


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


# Organization Category Schemas (TYPO3-Inspired Taxonomy Engine)
class OrganizationCategoryBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=150)
    slug: str | None = Field(default=None, max_length=150)
    icon: str | None = Field(default=None, max_length=50)
    description: str | None = None
    parent_id: str | None = None
    translations: dict[str, dict[str, str]] = Field(default_factory=dict)
    sort_order: int = 0
    is_active: bool = True


class OrganizationCategoryCreate(OrganizationCategoryBase):
    pass


class OrganizationCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    slug: str | None = Field(default=None, max_length=150)
    icon: str | None = Field(default=None, max_length=50)
    description: str | None = None
    parent_id: str | None = None
    translations: dict[str, dict[str, str]] | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class OrganizationCategoryRead(OrganizationCategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    slug: str
    forms_count: int = 0
    created_at: datetime
    updated_at: datetime


class PublicCategoryItem(BaseModel):
    id: str
    name: str
    slug: str
    icon: str | None = None
    description: str | None = None
    parent_id: str | None = None
    translations: dict[str, dict[str, str]] = Field(default_factory=dict)
    sort_order: int = 0
    forms_count: int = 0


# Public Portal & Directory Schemas (Phase G3)
class PublicPublishedFormItem(BaseModel):
    id: str
    key: str
    name: str
    description: str | None = None
    category: str = "general"
    category_id: str | None = None
    category_slug: str | None = None
    category_name: str | None = None
    submission_method: str = "print_and_sign"
    instructions: str | None = None
    required_documents: list[str] = Field(default_factory=list)
    active_version_id: str
    version_number: int = 1
    source_language: str = "de"
    supported_output_languages: list[str] = Field(default_factory=list)
    fields_count: int = 0
    has_pdf: bool = False


class PublicOrganizationSummary(BaseModel):
    id: str
    name: str
    slug: str
    organization_type: str = "government"
    verification_status: str = "unverified"
    is_verified_government: bool = False
    description: str | None = None
    office_address: str | None = None
    official_website_url: str | None = None
    has_logo: bool = False
    published_forms_count: int = 0
    supported_languages: list[str] = Field(default_factory=lambda: ["de", "en"])


class PublicOrganizationDetail(PublicOrganizationSummary):
    contact_email: str | None = None
    contact_phone: str | None = None
    cover_image_storage_path: str | None = None
    ui_theme_config: dict[str, Any] | None = None
    categories: list[PublicCategoryItem] = Field(default_factory=list)
    published_forms: list[PublicPublishedFormItem] = Field(default_factory=list)


# Phase G5-AI: Semantic Auto-Mapper Schemas
class AutoMapAlternativeSchema(BaseModel):
    key: str
    label: str
    confidence: float


class AutoMapFieldResultSchema(BaseModel):
    field_id: str
    field_key: str
    field_label: str
    current_question_key: str | None = None
    suggested_question_key: str | None = None
    confidence: float
    match_reason: str
    alternatives: list[AutoMapAlternativeSchema] = Field(default_factory=list)


class AutoMapResponseSchema(BaseModel):
    template_id: str
    total_fields: int
    mapped_fields_count: int
    suggestions: list[AutoMapFieldResultSchema]


class ApplyAutoMapItem(BaseModel):
    field_id: str
    question_key: str


class ApplyAutoMapRequestSchema(BaseModel):
    mappings: list[ApplyAutoMapItem]


class ApplyAutoMapResponseSchema(BaseModel):
    success: bool
    updated_fields_count: int
