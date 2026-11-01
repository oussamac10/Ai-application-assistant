import hashlib
import hmac
import logging
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.billing.models import OrganizationSubscription
from app.billing.schemas import OrganizationSubscriptionResponse, SubscriptionPlanInfo
from app.core.config import settings
from app.organizations.models import Organization, OrganizationCase

logger = logging.getLogger(__name__)

B2B_PLANS: dict[str, dict[str, Any]] = {
    "agency_sandbox": {
        "plan_key": "agency_sandbox",
        "name": "Agency Sandbox",
        "monthly_cases": 3,
        "price_eur": 0,
        "is_paid": False,
        "features": [
            "3 active candidate cases / month",
            "Universal 8-language intake preview",
            "Watermarked PDF inspection",
            "No credit card required",
        ],
    },
    "agency_pro": {
        "plan_key": "agency_pro",
        "name": "Agency Pro",
        "monthly_cases": 50,
        "price_eur": 149,
        "is_paid": True,
        "features": [
            "50 active candidate cases / month",
            "Full candidate invite links & magic-links",
            "Official unwatermarked PDF exports",
            "1-Click Profile Vault pre-fill",
            "Dual-Pane Verification Studio",
            "Standard business support",
        ],
    },
    "enterprise": {
        "plan_key": "enterprise",
        "name": "Enterprise & Public Sector",
        "monthly_cases": 200,
        "price_eur": 499,
        "is_paid": True,
        "features": [
            "200 active candidate cases / month",
            "Custom institutional form digitization SLA",
            "Dedicated enterprise DPA / GDPR agreements",
            "Multi-member case review & notes",
            "Priority phone & email support",
            "On-premise Docker deployment option",
        ],
    },
}


class BillingService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_available_plans(self) -> list[SubscriptionPlanInfo]:
        """Returns the public list of B2B subscription plans."""
        return [SubscriptionPlanInfo(**data) for data in B2B_PLANS.values()]

    def get_or_create_subscription(
        self, organization_id: str
    ) -> OrganizationSubscription:
        """Retrieves or creates the subscription record for an organization."""
        sub = self.db.execute(
            select(OrganizationSubscription).where(
                OrganizationSubscription.organization_id == organization_id
            )
        ).scalar_one_or_none()

        if sub is None:
            sub = OrganizationSubscription(
                organization_id=organization_id,
                plan_key="agency_sandbox",
                status="active",
                monthly_case_limit=B2B_PLANS["agency_sandbox"]["monthly_cases"],
            )
            self.db.add(sub)
            self.db.commit()
            self.db.refresh(sub)
        return sub

    def get_subscription_response(
        self, organization_id: str
    ) -> OrganizationSubscriptionResponse:
        """Returns detailed subscription information including current usage."""
        sub = self.get_or_create_subscription(organization_id)
        org = self.db.get(Organization, organization_id)
        effective_limit = (
            min(sub.monthly_case_limit, org.allowed_cases_per_month)
            if org
            else sub.monthly_case_limit
        )

        # Count cases created in current period or calendar month
        start_date = sub.current_period_start or datetime(
            datetime.now(UTC).year,
            datetime.now(UTC).month,
            1,
            tzinfo=UTC,
        )

        cases_used: int = (
            self.db.execute(
                select(func.count(OrganizationCase.id)).where(
                    OrganizationCase.organization_id == organization_id,
                    OrganizationCase.created_at >= start_date,
                )
            ).scalar()
            or 0
        )

        remaining = max(0, effective_limit - cases_used)

        return OrganizationSubscriptionResponse(
            id=sub.id,
            organization_id=sub.organization_id,
            plan_key=sub.plan_key,
            status=sub.status,
            monthly_case_limit=effective_limit,
            cases_used_this_period=cases_used,
            remaining_cases=remaining,
            current_period_start=sub.current_period_start,
            current_period_end=sub.current_period_end,
            cancel_at_period_end=sub.cancel_at_period_end,
        )

    def can_create_case(self, organization_id: str) -> tuple[bool, str | None]:
        """Checks if the organization has remaining quota to create a new candidate case."""
        info = self.get_subscription_response(organization_id)
        if info.remaining_cases <= 0:
            plan_name = B2B_PLANS.get(info.plan_key, {}).get("name", info.plan_key)
            return (
                False,
                f"Monthly case quota exceeded ({info.cases_used_this_period}/{info.monthly_case_limit}) for {plan_name}. Please upgrade to create more candidate cases.",
            )
        return True, None

    def create_checkout_session(
        self,
        *,
        organization_id: str,
        plan_key: str,
        success_url: str | None = None,
        cancel_url: str | None = None,
    ) -> tuple[str, str]:
        """Creates a Stripe Checkout Session for subscription upgrade."""
        if plan_key not in B2B_PLANS or plan_key == "agency_sandbox":
            raise ValueError(f"Invalid paid subscription plan: {plan_key}")

        org = self.db.get(Organization, organization_id)
        if not org:
            raise ValueError("Organization not found")

        frontend_url = settings.FRONTEND_BASE_URL.rstrip("/")
        s_url = (
            success_url
            or f"{frontend_url}/portal?session_id={{CHECKOUT_SESSION_ID}}&upgraded=true"
        )
        c_url = cancel_url or f"{frontend_url}/portal?canceled=true"

        # If Stripe is not configured or in testing without key, return mock sandbox session
        secret_key = settings.STRIPE_SECRET_KEY
        if not secret_key:
            logger.info(
                "STRIPE_SECRET_KEY not set; using local development checkout mock."
            )
            mock_session_id = f"cs_test_mock_{organization_id[:8]}_{plan_key}"
            mock_url = (
                f"{frontend_url}/portal?session_id={mock_session_id}&upgraded=true"
            )
            # Auto-upgrade subscription in dev/mock mode
            self.upgrade_plan(organization_id, plan_key)
            return mock_url, mock_session_id

        # Call Stripe REST API via httpx
        plan_meta = B2B_PLANS[plan_key]
        price_in_cents = plan_meta["price_eur"] * 100

        data = {
            "mode": "subscription",
            "success_url": s_url,
            "cancel_url": c_url,
            "client_reference_id": organization_id,
            "metadata[organization_id]": organization_id,
            "metadata[plan_key]": plan_key,
            "line_items[0][price_data][currency]": "eur",
            "line_items[0][price_data][product_data][name]": f"AI Form Assistant — {plan_meta['name']}",
            "line_items[0][price_data][recurring][interval]": "month",
            "line_items[0][price_data][unit_amount]": str(price_in_cents),
            "line_items[0][quantity]": "1",
        }

        sub = self.get_or_create_subscription(organization_id)
        if sub.stripe_customer_id:
            data["customer"] = sub.stripe_customer_id

        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                "https://api.stripe.com/v1/checkout/sessions",
                headers={"Authorization": f"Bearer {secret_key}"},
                data=data,
            )
            if resp.status_code != 200:
                logger.error("Stripe Checkout Session creation failed: %s", resp.text)
                raise RuntimeError(f"Stripe Checkout error: {resp.text}")
            result = resp.json()
            return str(result["url"]), str(result["id"])

    def create_customer_portal_session(
        self,
        *,
        organization_id: str,
        return_url: str | None = None,
    ) -> str:
        """Creates a Stripe Billing Customer Portal session to manage payment methods / invoices."""
        sub = self.get_or_create_subscription(organization_id)
        frontend_url = settings.FRONTEND_BASE_URL.rstrip("/")
        ret_url = return_url or f"{frontend_url}/portal"

        secret_key = settings.STRIPE_SECRET_KEY
        if not secret_key or not sub.stripe_customer_id:
            logger.info(
                "Stripe not configured or no customer ID; using local portal mock."
            )
            return ret_url

        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                "https://api.stripe.com/v1/billing_portal/sessions",
                headers={"Authorization": f"Bearer {secret_key}"},
                data={
                    "customer": sub.stripe_customer_id,
                    "return_url": ret_url,
                },
            )
            if resp.status_code != 200:
                logger.error("Stripe Portal session creation failed: %s", resp.text)
                raise RuntimeError(f"Stripe Customer Portal error: {resp.text}")
            return str(resp.json()["url"])

    def upgrade_plan(
        self,
        organization_id: str,
        plan_key: str,
        stripe_customer_id: str | None = None,
        stripe_subscription_id: str | None = None,
    ) -> OrganizationSubscription:
        """Upgrades the organization's subscription plan and updates case limits."""
        sub = self.get_or_create_subscription(organization_id)
        plan_meta = B2B_PLANS.get(plan_key, B2B_PLANS["agency_sandbox"])

        sub.plan_key = plan_key
        sub.status = "active"
        sub.monthly_case_limit = plan_meta["monthly_cases"]
        if stripe_customer_id:
            sub.stripe_customer_id = stripe_customer_id
        if stripe_subscription_id:
            sub.stripe_subscription_id = stripe_subscription_id

        # Also update parent Organization.billing_plan
        org = self.db.get(Organization, organization_id)
        if org:
            org.billing_plan = plan_key
            org.allowed_cases_per_month = plan_meta["monthly_cases"]

        self.db.commit()
        self.db.refresh(sub)
        return sub

    def verify_webhook_signature(self, payload: bytes, sig_header: str | None) -> bool:
        """Verifies the Stripe webhook signature."""
        secret = settings.STRIPE_WEBHOOK_SECRET
        if not secret:
            # If no webhook secret configured in dev, allow in non-production
            return not settings.is_production

        if not sig_header:
            return False

        try:
            parts = dict(
                item.split("=", 1) for item in sig_header.split(",") if "=" in item
            )
            timestamp = parts.get("t")
            v1_signature = parts.get("v1")
            if not timestamp or not v1_signature:
                return False

            signed_payload = f"{timestamp}.".encode() + payload
            expected = hmac.new(
                secret.encode("utf-8"),
                signed_payload,
                hashlib.sha256,
            ).hexdigest()
            return hmac.compare_digest(expected, v1_signature)
        except Exception as exc:
            logger.warning("Error verifying webhook signature: %s", exc)
            return False

    def process_webhook_event(self, event: dict[str, Any]) -> bool:
        """Processes verified Stripe webhook event idempotently."""
        event_type = event.get("type")
        data_obj = event.get("data", {}).get("object", {})

        if event_type == "checkout.session.completed":
            org_id = data_obj.get("metadata", {}).get(
                "organization_id"
            ) or data_obj.get("client_reference_id")
            plan_key = data_obj.get("metadata", {}).get("plan_key") or "agency_pro"
            customer_id = data_obj.get("customer")
            subscription_id = data_obj.get("subscription")

            if org_id:
                self.upgrade_plan(
                    org_id,
                    plan_key,
                    stripe_customer_id=customer_id,
                    stripe_subscription_id=subscription_id,
                )
                logger.info(
                    "Upgraded organization %s to %s via Stripe checkout",
                    org_id,
                    plan_key,
                )
                return True

        elif event_type == "customer.subscription.deleted":
            sub_id = data_obj.get("id")
            if sub_id:
                sub = self.db.execute(
                    select(OrganizationSubscription).where(
                        OrganizationSubscription.stripe_subscription_id == sub_id
                    )
                ).scalar_one_or_none()
                if sub:
                    sub.plan_key = "agency_sandbox"
                    sub.monthly_case_limit = B2B_PLANS["agency_sandbox"][
                        "monthly_cases"
                    ]
                    sub.status = "canceled"
                    self.db.commit()
                    logger.info(
                        "Subscription canceled for org %s; reverted to sandbox",
                        sub.organization_id,
                    )
                    return True

        return True
