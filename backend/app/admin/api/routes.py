"""Founder & Platform Admin API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin
from app.auth.models import User
from app.billing.models import AIUsageEvent, OrganizationSubscription
from app.core.config import settings
from app.database.session import get_db
from app.organizations.models import Organization, OrganizationCase, OrganizationMember

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/overview")
def get_admin_overview(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return aggregated platform KPIs, tenant roster, and system status for platform admins."""
    total_organizations = db.query(func.count(Organization.id)).scalar() or 0
    total_users = db.query(func.count(User.id)).scalar() or 0
    total_cases = db.query(func.count(OrganizationCase.id)).scalar() or 0

    # AI usage aggregates
    total_ai_events = db.query(func.count(AIUsageEvent.id)).scalar() or 0
    total_prompt_tokens = db.query(func.sum(AIUsageEvent.prompt_tokens)).scalar() or 0
    total_completion_tokens = (
        db.query(func.sum(AIUsageEvent.completion_tokens)).scalar() or 0
    )
    total_cost_eur = db.query(func.sum(AIUsageEvent.cost_eur)).scalar() or 0.0

    # Recent organizations with case count and active plan
    orgs = (
        db.query(Organization).order_by(Organization.created_at.desc()).limit(25).all()
    )
    org_list = []
    for org in orgs:
        member_count = (
            db.query(func.count(OrganizationMember.id))
            .filter(OrganizationMember.organization_id == org.id)
            .scalar()
            or 0
        )
        case_count = (
            db.query(func.count(OrganizationCase.id))
            .filter(OrganizationCase.organization_id == org.id)
            .scalar()
            or 0
        )
        sub = (
            db.query(OrganizationSubscription)
            .filter(OrganizationSubscription.organization_id == org.id)
            .first()
        )
        org_list.append(
            {
                "id": org.id,
                "name": org.name,
                "slug": org.slug,
                "created_at": org.created_at.isoformat() if org.created_at else None,
                "member_count": member_count,
                "case_count": case_count,
                "plan_key": sub.plan_key if sub else "agency_sandbox",
                "monthly_case_limit": sub.monthly_case_limit if sub else 3,
                "status": sub.status if sub else "active",
            }
        )

    return {
        "kpis": {
            "total_organizations": total_organizations,
            "total_users": total_users,
            "total_cases": total_cases,
            "total_ai_events": total_ai_events,
            "total_tokens": int(total_prompt_tokens + total_completion_tokens),
            "total_cost_eur": round(float(total_cost_eur), 4),
        },
        "firewall": {
            "max_session_cost_eur": 0.25,
            "ai_provider": settings.AI_PROVIDER,
            "translation_provider": settings.TRANSLATION_PROVIDER,
            "field_detection_provider": settings.FIELD_DETECTION_PROVIDER,
        },
        "organizations": org_list,
    }
