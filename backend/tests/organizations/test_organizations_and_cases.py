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


def _seed_published_form(
    *,
    required_documents: list[str] | None = None,
    submission_method: str = "in_person",
    instructions: str
    | None = "Print, sign, and bring your passport to the appointment.",
) -> str:
    db = SessionLocal()
    try:
        service = FormService(db)
        template = service.create_template(
            key="test-residence-permit",
            name="Official Residence Permit Application",
            description="Residence permit application test fixture",
        )
        template.required_documents = (
            required_documents
            if required_documents is not None
            else ["Valid passport", "Employment contract"]
        )
        template.submission_method = submission_method
        template.instructions = instructions
        db.flush()
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
    from app.auth.email_provider import clear_mock_email_outbox, get_mock_email_outbox

    clear_mock_email_outbox()
    _register(client, "manager@munich-expats.com")
    # Update org branding to verify white-label payload on invite inspection
    profile_res = client.patch(
        "/api/organizations/current",
        headers={"x-csrf-token": _csrf(client)},
        json={
            "name": "Munich Relocation Experts GmbH",
            "office_address": "Marienplatz 1, 80331 Munich",
            "contact_email": "support@munich-expats.com",
            "contact_phone": "+49 89 123456",
            "official_website_url": "https://munich-expats.com",
        },
    )
    assert profile_res.status_code == 200
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

    # 1b. Security check: raw URL invite token must NEVER directly unlock session APIs before OTP
    unauthenticated_client = TestClient(app)
    direct_session_res = unauthenticated_client.get(
        f"/api/form-sessions/{session_public_id}",
        headers={"X-Session-Token": raw_invite_token},
    )
    assert direct_session_res.status_code == 401

    # 2. Safe public invite inspection returns branding + checklist WITHOUT session token
    inspect_res = unauthenticated_client.get(f"/api/cases/invite/{raw_invite_token}")
    assert inspect_res.status_code == 200
    inspect_data = inspect_res.json()
    assert "session_token" not in inspect_data
    assert "session_id" not in inspect_data
    assert inspect_data["candidate_name"] == "Dr. Sarah Connor"
    assert inspect_data["masked_email"] == "s***r@cyberdyne.org"
    assert inspect_data["otp_verified"] is False
    assert inspect_data["required_documents"] == [
        "Valid passport",
        "Employment contract",
    ]
    assert inspect_data["submission_method"] == "in_person"
    assert (
        inspect_data["instructions"]
        == "Print, sign, and bring your passport to the appointment."
    )
    assert inspect_data["organization"]["name"] == "Munich Relocation Experts GmbH"
    assert (
        inspect_data["organization"]["office_address"] == "Marienplatz 1, 80331 Munich"
    )
    assert inspect_data["organization"]["contact_email"] == "support@munich-expats.com"

    # 3. Candidate requests 6-digit OTP and receives it in mock email outbox
    clear_mock_email_outbox()
    otp_send_res = unauthenticated_client.post(
        f"/api/cases/invite/{raw_invite_token}/send-otp"
    )
    assert otp_send_res.status_code == 200
    assert otp_send_res.json()["sent"] is True
    assert "otp_code" not in otp_send_res.json()
    otp_emails = [m for m in get_mock_email_outbox() if m.purpose == "candidate_otp"]
    assert len(otp_emails) == 1
    otp_code = otp_emails[0].token
    assert len(otp_code) == 6 and otp_code.isdigit()

    # 4. Candidate verifies OTP and unlocks the form session with a freshly minted token
    verify_res = unauthenticated_client.post(
        f"/api/cases/invite/{raw_invite_token}/verify-otp",
        json={"otp_code": otp_code},
    )
    assert verify_res.status_code == 200
    intake_data = verify_res.json()
    assert intake_data["candidate_name"] == "Dr. Sarah Connor"
    assert intake_data["session_id"] == session_public_id
    assert intake_data["session_token"] != raw_invite_token
    assert intake_data["status"] == "in_progress"
    assert intake_data["required_documents"] == [
        "Valid passport",
        "Employment contract",
    ]

    # Single-use OTP cannot be replayed
    replay_res = unauthenticated_client.post(
        f"/api/cases/invite/{raw_invite_token}/verify-otp",
        json={"otp_code": otp_code},
    )
    assert replay_res.status_code == 400

    # 5. Candidate uses verified session token to inspect SessionResponse metadata
    session_res = unauthenticated_client.get(
        f"/api/form-sessions/{session_public_id}",
        headers={"X-Session-Token": intake_data["session_token"]},
    )
    assert session_res.status_code == 200
    session_json = session_res.json()
    assert session_json["sessionId"] == session_public_id
    assert session_json["isSponsoredCase"] is True
    assert session_json["organizationName"] == "Munich Relocation Experts GmbH"
    assert session_json["requiredDocuments"] == [
        "Valid passport",
        "Employment contract",
    ]
    assert session_json["submissionMethod"] == "in_person"

    # 6. Agency manager lists cases and sees status + audit timestamps
    list_res = client.get("/api/cases")
    assert list_res.status_code == 200
    cases_list = list_res.json()
    assert len(cases_list) == 1
    assert cases_list[0]["public_id"] == case_public_id
    assert cases_list[0]["status"] == "in_progress"
    assert cases_list[0]["otp_verified_at"] is not None
    assert cases_list[0]["last_accessed_at"] is not None


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


def test_otp_brute_force_lockout_and_expiry() -> None:
    from datetime import UTC, datetime, timedelta

    from app.auth.email_provider import clear_mock_email_outbox, get_mock_email_outbox
    from app.organizations.models import OrganizationCase

    clear_mock_email_outbox()
    _register(client, "security@agency.de")
    form_version_id = _seed_published_form()

    res = client.post(
        "/api/cases",
        headers={"x-csrf-token": _csrf(client)},
        json={
            "candidate_name": "Brute Force Test",
            "candidate_email": "victim@example.com",
            "form_version_id": form_version_id,
        },
    )
    assert res.status_code == 201
    raw_token = res.json()["invite_token"]
    case_pub_id = res.json()["public_id"]

    anon = TestClient(app)
    clear_mock_email_outbox()
    assert anon.post(f"/api/cases/invite/{raw_token}/send-otp").status_code == 200
    real_otp = [m for m in get_mock_email_outbox() if m.purpose == "candidate_otp"][
        0
    ].token
    wrong_otp = "999999" if real_otp != "999999" else "000000"

    # 5 wrong attempts invalidate the active OTP code
    for _ in range(5):
        bad = anon.post(
            f"/api/cases/invite/{raw_token}/verify-otp",
            json={"otp_code": wrong_otp},
        )
        assert bad.status_code == 400

    # Even submitting the real OTP must now fail until a fresh code is requested
    locked = anon.post(
        f"/api/cases/invite/{raw_token}/verify-otp",
        json={"otp_code": real_otp},
    )
    assert locked.status_code == 400

    # Request a fresh OTP, then expire it in DB
    clear_mock_email_outbox()
    assert anon.post(f"/api/cases/invite/{raw_token}/send-otp").status_code == 200
    fresh_otp = [m for m in get_mock_email_outbox() if m.purpose == "candidate_otp"][
        0
    ].token

    db = SessionLocal()
    try:
        case = db.query(OrganizationCase).filter_by(public_id=case_pub_id).first()
        assert case is not None
        case.otp_expires_at = datetime.now(UTC) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()

    expired = anon.post(
        f"/api/cases/invite/{raw_token}/verify-otp",
        json={"otp_code": fresh_otp},
    )
    assert expired.status_code == 400
    assert "expired" in expired.json()["detail"].lower()


def test_revoke_case_invite_invalidates_link_and_session() -> None:
    from app.auth.email_provider import clear_mock_email_outbox, get_mock_email_outbox

    clear_mock_email_outbox()
    _register(client, "owner@relocation.de")
    _register(other_client, "attacker@other.de")
    form_version_id = _seed_published_form()

    create_res = client.post(
        "/api/cases",
        headers={"x-csrf-token": _csrf(client)},
        json={
            "candidate_name": "Revoke Target",
            "candidate_email": "target@example.com",
            "form_version_id": form_version_id,
        },
    )
    assert create_res.status_code == 201
    case_pub_id = create_res.json()["public_id"]
    raw_token = create_res.json()["invite_token"]

    # Unlock OTP to get an active session token first
    anon = TestClient(app)
    clear_mock_email_outbox()
    assert anon.post(f"/api/cases/invite/{raw_token}/send-otp").status_code == 200
    otp_code = [m for m in get_mock_email_outbox() if m.purpose == "candidate_otp"][
        0
    ].token
    verify_res = anon.post(
        f"/api/cases/invite/{raw_token}/verify-otp",
        json={"otp_code": otp_code},
    )
    assert verify_res.status_code == 200
    session_id = verify_res.json()["session_id"]
    session_token = verify_res.json()["session_token"]

    # Cross-tenant revoke rejected (404) and missing CSRF rejected (401)
    assert (
        other_client.post(
            f"/api/cases/{case_pub_id}/revoke-invite",
            headers={"x-csrf-token": _csrf(other_client)},
        ).status_code
        == 404
    )
    assert client.post(f"/api/cases/{case_pub_id}/revoke-invite").status_code == 401

    # Owner revokes invite
    revoke_res = client.post(
        f"/api/cases/{case_pub_id}/revoke-invite",
        headers={"x-csrf-token": _csrf(client)},
    )
    assert revoke_res.status_code == 200
    revoked_case = revoke_res.json()
    assert revoked_case["status"] == "revoked"
    assert revoked_case["revoked_at"] is not None

    # Invite link and previously issued session token are both invalid immediately
    assert anon.get(f"/api/cases/invite/{raw_token}").status_code == 400
    assert (
        anon.get(
            f"/api/form-sessions/{session_id}",
            headers={"X-Session-Token": session_token},
        ).status_code
        == 401
    )


def test_resend_case_invite_rotates_token_and_increments_count() -> None:
    from app.auth.email_provider import clear_mock_email_outbox, get_mock_email_outbox

    _register(client, "ops@relocation.de")
    form_version_id = _seed_published_form()

    create_res = client.post(
        "/api/cases",
        headers={"x-csrf-token": _csrf(client)},
        json={
            "candidate_name": "Resend Target",
            "candidate_email": "resend@example.com",
            "form_version_id": form_version_id,
        },
    )
    assert create_res.status_code == 201
    case_pub_id = create_res.json()["public_id"]
    old_token = create_res.json()["invite_token"]

    clear_mock_email_outbox()
    resend_res = client.post(
        f"/api/cases/{case_pub_id}/resend-invite",
        headers={"x-csrf-token": _csrf(client)},
    )
    assert resend_res.status_code == 200
    resent_case = resend_res.json()
    new_token = resent_case["invite_token"]
    assert new_token is not None and new_token != old_token
    assert resent_case["resend_count"] == 1
    assert resent_case["last_resent_at"] is not None
    assert resent_case["status"] == "invited"

    invite_emails = [
        m for m in get_mock_email_outbox() if m.purpose == "candidate_invite"
    ]
    assert len(invite_emails) == 1
    assert invite_emails[0].token == new_token

    anon = TestClient(app)
    assert anon.get(f"/api/cases/invite/{old_token}").status_code == 400
    assert anon.get(f"/api/cases/invite/{new_token}").status_code == 200


def test_starter_templates_include_checklists_and_instructions() -> None:
    _register(client, "starter@relocation.de")
    prov_res = client.post(
        "/api/organizations/current/forms/starter-templates",
        headers={"x-csrf-token": _csrf(client)},
    )
    assert prov_res.status_code == 200
    assert prov_res.json()["provisionedCount"] == 3

    forms_res = client.get("/api/organizations/current/forms")
    assert forms_res.status_code == 200
    forms = forms_res.json()
    assert len(forms) == 3
    for f in forms:
        assert len(f["requiredDocuments"]) >= 2
        assert f["instructions"]
        assert f["submissionMethod"] in (
            "in_person",
            "print_and_sign",
            "online",
            "email",
        )
