import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ai.guardrails import (
    get_session_cumulative_cost,
    is_session_budget_exceeded,
    record_ai_usage,
)
from app.database.session import SessionLocal
from app.forms.models import FormField, FormTemplate, FormVersion
from app.main import app


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE organizations CASCADE"))
        db.execute(text("TRUNCATE TABLE users CASCADE"))
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.execute(text("TRUNCATE TABLE ai_usage_events CASCADE"))
        db.commit()
        yield db
    finally:
        db.close()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _seed_test_form(db: Session) -> FormVersion:
    tmpl = FormTemplate(
        id=str(uuid.uuid4()),
        key=f"test-visa-{uuid.uuid4().hex[:6]}",
        name="Global Talent Visa",
        description="Standard global visa intake form",
    )
    db.add(tmpl)
    ver = FormVersion(
        id=str(uuid.uuid4()),
        form_template_id=tmpl.id,
        version_number=1,
        source_language="en",
        supported_output_languages=["en"],
        status="published",
        origin="predefined_template",
    )
    db.add(ver)
    fld = FormField(
        id=str(uuid.uuid4()),
        form_version_id=ver.id,
        key="full_name",
        field_type="string",
        required=True,
        position=1,
    )
    db.add(fld)
    db.commit()
    db.refresh(ver)
    return ver


PASSWORD = "ValidPassword123!"


def _register(c: TestClient, email: str = "agent@relocation.com") -> str:
    res = c.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "passwordConfirmation": PASSWORD,
        },
    )
    assert res.status_code == 201
    return str(res.json()["id"])


def _csrf(c: TestClient) -> str:
    token = c.cookies.get("csrf_token")
    assert token
    return token


def test_list_plans_returns_b2b_tiers(client: TestClient) -> None:
    res = client.get("/api/billing/plans")
    assert res.status_code == 200
    plans = res.json()
    keys = {p["plan_key"] for p in plans}
    assert "agency_sandbox" in keys
    assert "agency_pro" in keys
    assert "enterprise" in keys

    pro = next(p for p in plans if p["plan_key"] == "agency_pro")
    assert pro["price_eur"] == 149
    assert pro["monthly_cases"] == 50
    assert pro["is_paid"] is True


def test_get_subscription_defaults_to_sandbox(
    client: TestClient, db_session: Session
) -> None:
    _register(client, "agent_sub@relocation.com")
    res = client.get("/api/billing/subscription")
    assert res.status_code == 200
    data = res.json()
    assert data["plan_key"] == "agency_sandbox"
    assert data["monthly_case_limit"] == 3
    assert data["cases_used_this_period"] == 0
    assert data["remaining_cases"] == 3


def test_case_creation_enforces_sandbox_quota_and_upgrades(
    client: TestClient, db_session: Session
) -> None:
    _register(client, "agent_quota@relocation.com")
    form_ver = _seed_test_form(db_session)

    # 1. Create 3 cases (the sandbox limit)
    csrf_token = _csrf(client)
    headers = {"X-CSRF-Token": csrf_token}

    for i in range(3):
        create_res = client.post(
            "/api/cases",
            headers=headers,
            json={
                "candidate_name": f"Candidate {i + 1}",
                "candidate_email": f"candidate{i + 1}@example.com",
                "form_version_id": form_ver.id,
                "user_language": "fr",
            },
        )
        assert create_res.status_code == 201, create_res.text

    # Verify quota shows 3/3 used, 0 remaining
    sub_res = client.get("/api/billing/subscription")
    assert sub_res.status_code == 200
    assert sub_res.json()["cases_used_this_period"] == 3
    assert sub_res.json()["remaining_cases"] == 0

    # 2. 4th case must be rejected with 402 Payment Required
    rejected_res = client.post(
        "/api/cases",
        headers=headers,
        json={
            "candidate_name": "Candidate 4 (Over Quota)",
            "candidate_email": "candidate4@example.com",
            "form_version_id": form_ver.id,
            "user_language": "en",
        },
    )
    assert rejected_res.status_code == 402
    assert "quota exceeded" in rejected_res.json()["detail"].lower()

    # 3. Upgrade to Agency Pro via Checkout endpoint
    current_org = client.get("/api/organizations/current").json()
    org_id = current_org["id"]

    checkout_res = client.post(
        "/api/billing/checkout",
        headers=headers,
        json={
            "organization_id": org_id,
            "plan_key": "agency_pro",
        },
    )
    assert checkout_res.status_code == 200
    assert "session_id" in checkout_res.json()

    # Check updated quota: 50 cases limit, 47 remaining
    upgraded_sub = client.get("/api/billing/subscription").json()
    assert upgraded_sub["plan_key"] == "agency_pro"
    assert upgraded_sub["monthly_case_limit"] == 50
    assert upgraded_sub["remaining_cases"] == 47

    # 4. Now 4th candidate case creation succeeds
    success_res = client.post(
        "/api/cases",
        headers=headers,
        json={
            "candidate_name": "Candidate 4 (Allowed)",
            "candidate_email": "candidate4@example.com",
            "form_version_id": form_ver.id,
            "user_language": "en",
        },
    )
    assert success_res.status_code == 201


def test_stripe_webhook_lifecycle(client: TestClient, db_session: Session) -> None:
    _register(client, email="webhook_test@agency.com")
    current_org = client.get("/api/organizations/current").json()
    org_id = current_org["id"]

    # 1. Simulate checkout.session.completed for Enterprise upgrade
    checkout_event = {
        "id": "evt_test_123",
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "id": "cs_test_enterprise",
                "customer": "cus_test_999",
                "subscription": "sub_test_enterprise_888",
                "client_reference_id": org_id,
                "metadata": {
                    "organization_id": org_id,
                    "plan_key": "enterprise",
                },
            }
        },
    }

    wh_res = client.post("/api/billing/webhook", json=checkout_event)
    assert wh_res.status_code == 200

    sub_info = client.get("/api/billing/subscription").json()
    assert sub_info["plan_key"] == "enterprise"
    assert sub_info["monthly_case_limit"] == 200

    # 2. Simulate customer.subscription.deleted -> reverts to sandbox
    cancel_event = {
        "id": "evt_test_456",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_test_enterprise_888",
                "customer": "cus_test_999",
            }
        },
    }
    wh_cancel_res = client.post("/api/billing/webhook", json=cancel_event)
    assert wh_cancel_res.status_code == 200

    reverted_sub = client.get("/api/billing/subscription").json()
    assert reverted_sub["plan_key"] == "agency_sandbox"
    assert reverted_sub["monthly_case_limit"] == 3


def test_ai_usage_ledger_and_spend_circuit_breaker(
    client: TestClient, db_session: Session
) -> None:
    _register(client, "agent_ai_usage@test.com")
    form_ver = _seed_test_form(db_session)
    csrf_token = _csrf(client)
    headers = {"X-CSRF-Token": csrf_token}

    case_res = client.post(
        "/api/cases",
        headers=headers,
        json={
            "candidate_name": "AI Usage Candidate",
            "candidate_email": "candidate.ai@example.com",
            "form_version_id": form_ver.id,
            "user_language": "en",
        },
    )
    assert case_res.status_code == 201
    session_id = case_res.json()["form_session_id"]

    # Initially zero
    cost_0 = get_session_cumulative_cost(db_session, session_id)
    assert cost_0 == 0.0
    assert not is_session_budget_exceeded(db_session, session_id, limit_eur=0.25)

    # Record small LLM calls (e.g. 500 tokens)
    record_ai_usage(
        db_session,
        provider="gemini",
        operation="explanation",
        prompt_tokens=500,
        completion_tokens=200,
        session_id=session_id,
    )
    cost_1 = get_session_cumulative_cost(db_session, session_id)
    assert 0.0 < cost_1 < 0.01
    assert not is_session_budget_exceeded(db_session, session_id, limit_eur=0.25)

    # Record large OCR / document call exceeding limit
    record_ai_usage(
        db_session,
        provider="azure_doc_intel",
        operation="detection",
        cost_eur=0.26,
        session_id=session_id,
    )
    cost_2 = get_session_cumulative_cost(db_session, session_id)
    assert cost_2 > 0.25
    assert is_session_budget_exceeded(db_session, session_id, limit_eur=0.25)
