from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database.session import SessionLocal
from app.forms.schemas import FieldCreate, TranslationSchema
from app.forms.services import FormService
from app.main import app

PASSWORD = "AgencySecretPassword123!"

client = TestClient(app)
other_client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    client.cookies.clear()
    other_client.cookies.clear()
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE organizations CASCADE"))
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.execute(text("TRUNCATE TABLE users CASCADE"))
        db.commit()
        yield
    except Exception:
        db.rollback()
    finally:
        db.close()
        client.cookies.clear()
        other_client.cookies.clear()


def _register(c: TestClient, email: str = "case-manager@relocation-agency.de") -> str:
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


def _seed_published_form() -> str:
    db = SessionLocal()
    try:
        service = FormService(db)
        template = service.create_template(
            key="test-residence-permit",
            name="Official Residence Permit Application",
            description="Residence permit application test fixture",
        )
        version = service.create_draft_version(
            form_template_id=template.id,
            source_language="de",
            supported_output_languages=["de", "en"],
            origin="predefined_template",
            pdf_template_key="test-permit-v1",
        )
        fields = [
            FieldCreate(
                key="personal.first_name",
                field_type="text",
                position=1,
                required=True,
                translations=[
                    TranslationSchema(
                        language="de",
                        label="Vorname",
                        help_text="Ihr Vorname",
                    ),
                    TranslationSchema(
                        language="en",
                        label="First Name",
                        help_text="Your given name",
                    ),
                ],
            ),
            FieldCreate(
                key="personal.last_name",
                field_type="text",
                position=2,
                required=True,
                translations=[
                    TranslationSchema(
                        language="de",
                        label="Familienname",
                        help_text="Ihr Familienname",
                    ),
                    TranslationSchema(
                        language="en",
                        label="Surname",
                        help_text="Your family name",
                    ),
                ],
            ),
        ]
        for f in fields:
            service.add_field_to_draft(version.id, f)
        published = service.publish_version(version.id)
        return published.id
    finally:
        db.close()


def test_ensure_default_organization_and_get_current() -> None:
    _register(client, "hans.schmidt@berlin-relocation.de")

    res = client.get("/api/organizations/current")
    assert res.status_code == 200
    data = res.json()
    assert "Berlin-relocation" in data["name"] or "Hans.schmidt" in data["name"]
    assert data["billing_plan"] in ("agency_sandbox", "agency_pro")
    assert data["allowed_cases_per_month"] in (3, 50)
    assert data["role"] == "owner"


def test_create_case_and_magic_link_flow() -> None:
    _register(client, "manager@munich-expats.com")
    form_version_id = _seed_published_form()

    # 1. Create a candidate case
    res = client.post(
        "/api/cases",
        headers={"x-csrf-token": _csrf(client)},
        json={
            "candidate_name": "Dr. Sarah Connor",
            "candidate_email": "sarah.connor@cyberdyne.org",
            "form_version_id": form_version_id,
            "user_language": "en",
            "notes": "Fast-track Blue Card visa candidate",
        },
    )
    assert res.status_code == 201
    case_data = res.json()
    assert case_data["candidate_name"] == "Dr. Sarah Connor"
    assert case_data["candidate_email"] == "sarah.connor@cyberdyne.org"
    assert case_data["status"] == "invited"
    assert case_data["form_title"] == "Official Residence Permit Application"
    assert case_data["total_fields"] == 2
    assert case_data["answered_fields"] == 0
    assert case_data["progress_percent"] == 0
    assert case_data["invite_token"] is not None

    raw_invite_token = case_data["invite_token"]
    case_public_id = case_data["public_id"]
    session_public_id = case_data["session_public_id"]

    # 2. Public candidate magic-link redemption (unauthenticated candidate)
    unauthenticated_client = TestClient(app)
    invite_res = unauthenticated_client.get(f"/api/cases/invite/{raw_invite_token}")
    assert invite_res.status_code == 200
    intake_data = invite_res.json()
    assert intake_data["candidate_name"] == "Dr. Sarah Connor"
    assert intake_data["session_id"] == session_public_id
    assert intake_data["session_token"] == raw_invite_token
    assert intake_data["status"] == "in_progress"

    # 3. Candidate uses raw token to interact with their session
    session_res = unauthenticated_client.get(
        f"/api/form-sessions/{session_public_id}",
        headers={"X-Session-Token": raw_invite_token},
    )
    assert session_res.status_code == 200
    assert session_res.json()["sessionId"] == session_public_id

    # 4. Agency manager lists cases and sees status updated to "in_progress"
    list_res = client.get("/api/cases")
    assert list_res.status_code == 200
    cases_list = list_res.json()
    assert len(cases_list) == 1
    assert cases_list[0]["public_id"] == case_public_id
    assert cases_list[0]["status"] == "in_progress"


def test_invalid_or_unknown_invite_token() -> None:
    unauthenticated_client = TestClient(app)
    res = unauthenticated_client.get("/api/cases/invite/invalid-token-12345")
    assert res.status_code == 400
    assert "Invalid or expired" in res.json()["detail"]


def test_cross_tenant_case_isolation() -> None:
    _register(client, "agency-a@test.com")
    _register(other_client, "agency-b@test.com")
    form_version_id = _seed_published_form()

    # Agency A creates a case
    res_a = client.post(
        "/api/cases",
        headers={"x-csrf-token": _csrf(client)},
        json={
            "candidate_name": "Candidate A",
            "candidate_email": "candidate.a@test.com",
            "form_version_id": form_version_id,
            "user_language": "en",
        },
    )
    assert res_a.status_code == 201
    case_a_id = res_a.json()["public_id"]

    # Agency B tries to get Agency A's case -> 404
    res_b = other_client.get(f"/api/cases/{case_a_id}")
    assert res_b.status_code == 404

    # Agency B lists cases -> empty
    list_b = other_client.get("/api/cases")
    assert list_b.status_code == 200
    assert len(list_b.json()) == 0


def test_update_case_status_and_notes() -> None:
    _register(client, "lead@agency.de")
    form_version_id = _seed_published_form()

    res = client.post(
        "/api/cases",
        headers={"x-csrf-token": _csrf(client)},
        json={
            "candidate_name": "Candidate Review",
            "candidate_email": "review@test.com",
            "form_version_id": form_version_id,
        },
    )
    case_id = res.json()["public_id"]

    # Update status to completed and add review notes
    patch_res = client.patch(
        f"/api/cases/{case_id}",
        headers={"x-csrf-token": _csrf(client)},
        json={
            "status": "completed",
            "notes": "Reviewed and submitted to Ausländerbehörde Munich.",
        },
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["status"] == "completed"
    assert updated["notes"] == "Reviewed and submitted to Ausländerbehörde Munich."


def test_quota_enforcement() -> None:
    _register(client, "quota-tester@agency.com")
    form_version_id = _seed_published_form()

    # Call endpoint to ensure default org exists
    client.get("/api/organizations/current")

    # Lower quota directly for testing
    db = SessionLocal()
    try:
        from app.organizations.models import Organization

        org = db.query(Organization).first()
        assert org
        org.allowed_cases_per_month = 1
        db.commit()
    finally:
        db.close()

    # First case succeeds
    res1 = client.post(
        "/api/cases",
        headers={"x-csrf-token": _csrf(client)},
        json={
            "candidate_name": "Case 1",
            "candidate_email": "case1@test.com",
            "form_version_id": form_version_id,
        },
    )
    assert res1.status_code == 201

    # Second case fails with 402 Quota Exceeded
    res2 = client.post(
        "/api/cases",
        headers={"x-csrf-token": _csrf(client)},
        json={
            "candidate_name": "Case 2",
            "candidate_email": "case2@test.com",
            "form_version_id": form_version_id,
        },
    )
    assert res2.status_code == 402
    assert "quota exceeded" in res2.json()["detail"].lower()
