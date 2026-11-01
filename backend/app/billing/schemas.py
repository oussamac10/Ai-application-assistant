from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class SubscriptionPlanInfo(BaseModel):
    plan_key: str
    name: str
    monthly_cases: int
    price_eur: int
    is_paid: bool
    features: list[str] = Field(default_factory=list)


class OrganizationSubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    organization_id: str
    plan_key: str
    status: str
    monthly_case_limit: int
    cases_used_this_period: int
    remaining_cases: int
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool = False


class CreateCheckoutSessionRequest(BaseModel):
    organization_id: str
    plan_key: str
    success_url: str | None = None
    cancel_url: str | None = None


class CheckoutSessionResponse(BaseModel):
    checkout_url: str
    session_id: str


class CreatePortalSessionRequest(BaseModel):
    organization_id: str
    return_url: str | None = None


class PortalSessionResponse(BaseModel):
    portal_url: str
