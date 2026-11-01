import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_user, verify_csrf
from app.auth.models import User
from app.billing.schemas import (
    CheckoutSessionResponse,
    CreateCheckoutSessionRequest,
    CreatePortalSessionRequest,
    OrganizationSubscriptionResponse,
    PortalSessionResponse,
    SubscriptionPlanInfo,
)
from app.billing.services import BillingService
from app.database.session import get_db
from app.organizations.services import OrganizationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/plans", response_model=list[SubscriptionPlanInfo])
def list_plans(db: Session = Depends(get_db)) -> Any:
    """Lists available B2B subscription plans."""
    service = BillingService(db)
    return service.list_available_plans()


@router.get("/subscription", response_model=OrganizationSubscriptionResponse)
def get_current_subscription(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> Any:
    """Retrieves subscription details and current usage for the caller's organization."""
    org_service = OrganizationService(db)
    org, _ = org_service.ensure_default_organization(user)
    billing_service = BillingService(db)
    return billing_service.get_subscription_response(org.id)


@router.post("/checkout", response_model=CheckoutSessionResponse)
def create_checkout_session(
    body: CreateCheckoutSessionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    """Initiates a Stripe Checkout session for subscription upgrade."""
    org_service = OrganizationService(db)
    org, _ = org_service.ensure_default_organization(user)
    if body.organization_id != org.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot create checkout session for an organization you do not manage.",
        )

    billing_service = BillingService(db)
    try:
        url, session_id = billing_service.create_checkout_session(
            organization_id=org.id,
            plan_key=body.plan_key,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
        )
        return CheckoutSessionResponse(checkout_url=url, session_id=session_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    except Exception as exc:
        logger.error("Checkout creation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to initiate payment checkout.",
        ) from exc


@router.post("/portal", response_model=PortalSessionResponse)
def create_portal_session(
    body: CreatePortalSessionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    """Creates a Stripe Billing Customer Portal session to manage invoices and cards."""
    org_service = OrganizationService(db)
    org, _ = org_service.ensure_default_organization(user)
    if body.organization_id != org.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access billing portal for an organization you do not manage.",
        )

    billing_service = BillingService(db)
    try:
        portal_url = billing_service.create_customer_portal_session(
            organization_id=org.id,
            return_url=body.return_url,
        )
        return PortalSessionResponse(portal_url=portal_url)
    except Exception as exc:
        logger.error("Portal session creation failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to access billing portal.",
        ) from exc


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
) -> Response:
    """Stripe Webhook handler with cryptographic HMAC signature verification."""
    payload = await request.body()
    service = BillingService(db)

    if not service.verify_webhook_signature(payload, stripe_signature):
        logger.warning("Rejected unverified Stripe webhook payload")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe signature",
        )

    try:
        event = json.loads(payload.decode("utf-8"))
        service.process_webhook_event(event)
        return Response(status_code=status.HTTP_200_OK, content="OK")
    except Exception as exc:
        logger.error("Error processing Stripe webhook: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook processing error",
        ) from exc
