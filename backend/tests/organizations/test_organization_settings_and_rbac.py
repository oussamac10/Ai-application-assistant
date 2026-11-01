from collections.abc import Generator
from io import BytesIO

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database.session import SessionLocal
from app.main import app


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE organizations CASCADE"))
        db.execute(text("TRUNCATE TABLE users CASCADE"))
        db.commit()
        yield db
    finally:
        db.close()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)


def _register_and_auth(client: TestClient, email: str) -> None:
    res = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "SecurePassword123!",
            "passwordConfirmation": "SecurePassword123!",
        },
    )
    assert res.status_code == 201
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


def test_organization_profile_update_and_verification(
    client: TestClient, db_session: Session
) -> None:
    _register_and_auth(client, "rathaus@stuttgart.de")

    # 1. Get current org
    res = client.get("/api/organizations/current")
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "owner"
    assert data["verification_status"] == "unverified"
    assert data["is_verified_government"] is False

    # 2. Update profile
    patch_res = client.patch(
        "/api/organizations/current",
        json={
            "name": "Stadt Stuttgart - Bürgerbüro",
            "description": "Zentraler Bürgerservice der Landeshauptstadt Stuttgart.",
            "office_address": "Marktplatz 1, 70173 Stuttgart",
            "contact_email": "kontakt@stuttgart.de",
            "contact_phone": "+49 711 216 0",
            "official_website_url": "https://www.stuttgart.de",
            "supported_languages": ["de", "en", "ar", "fr"],
        },
    )
    assert patch_res.status_code == 200
    updated = patch_res.json()
    assert updated["name"] == "Stadt Stuttgart - Bürgerbüro"
    assert updated["contact_email"] == "kontakt@stuttgart.de"
    assert updated["supported_languages"] == ["de", "en", "ar", "fr"]

    # 3. Submit official verification request
    verif_res = client.post(
        "/api/organizations/current/verification",
        json={
            "authority_name": "Landeshauptstadt Stuttgart",
            "registration_id": "DE-BW-STG-08111000",
            "official_domain": "stuttgart.de",
            "contact_person_title": "Amtsleitung Bürgerservice",
            "notes": "Offizielle Registrierung der Kommunalbehörde Stuttgart.",
        },
    )
    assert verif_res.status_code == 200
    assert verif_res.json()["verification_status"] == "pending_review"

    # 4. Super Admin reviews and approves verification
    admin_client = TestClient(app)
    settings.ADMIN_EMAILS = "admin@platform.gov"
    _register_and_auth(admin_client, "admin@platform.gov")

    queue_res = admin_client.get("/api/admin/verifications")
    assert queue_res.status_code == 200
    pending_list = queue_res.json()
    assert len(pending_list) >= 1
    org_id = updated["id"]

    approve_res = admin_client.post(f"/api/admin/verifications/{org_id}/approve")
    assert approve_res.status_code == 200
    assert approve_res.json()["is_verified_government"] is True
    assert approve_res.json()["verification_status"] == "verified_official"

    # 5. Organization verifies approved status
    recheck = client.get("/api/organizations/current")
    assert recheck.json()["is_verified_government"] is True
    assert recheck.json()["verification_status"] == "verified_official"


def test_member_invitation_and_rbac(client: TestClient, db_session: Session) -> None:
    _register_and_auth(client, "lead@amt.de")

    # Invite a case manager
    invite_res = client.post(
        "/api/organizations/current/members",
        json={"email": "officer@amt.de", "role": "case_manager"},
    )
    assert invite_res.status_code == 201
    member = invite_res.json()
    assert member["email"] == "officer@amt.de"
    assert member["role"] == "case_manager"
    member_user_id = member["user_id"]

    # List members
    list_res = client.get("/api/organizations/current/members")
    assert list_res.status_code == 200
    members = list_res.json()
    assert len(members) == 2

    # Promote officer to admin
    role_res = client.patch(
        f"/api/organizations/current/members/{member_user_id}",
        json={"role": "admin"},
    )
    assert role_res.status_code == 200
    assert role_res.json()["role"] == "admin"

    # Remove officer
    del_res = client.delete(f"/api/organizations/current/members/{member_user_id}")
    assert del_res.status_code == 204

    # Officer is removed
    list_after = client.get("/api/organizations/current/members").json()
    assert len(list_after) == 1


def test_logo_branding_upload(client: TestClient, db_session: Session) -> None:
    _register_and_auth(client, "stadt@freiburg.de")

    fake_png = BytesIO(b"\x89PNG\r\n\x1a\n" + b"fake-image-bytes" * 50)
    upload_res = client.post(
        "/api/organizations/current/logo",
        files={"file": ("freiburg-logo.png", fake_png, "image/png")},
    )
    assert upload_res.status_code == 200
    data = upload_res.json()
    assert data["logo_storage_path"] is not None
    assert "logo-" in data["logo_storage_path"]

    # Test GET logo serving
    get_res = client.get("/api/organizations/current/logo")
    assert get_res.status_code == 200
    assert get_res.headers["content-type"] == "image/png"
    assert get_res.content.startswith(b"\x89PNG")

    # Upload SVG logo
    fake_svg = BytesIO(
        b"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><circle cx='50' cy='50' r='40'/></svg>"
    )
    upload_svg = client.post(
        "/api/organizations/current/logo",
        files={"file": ("stuttgart-seal.svg", fake_svg, "image/svg+xml")},
    )
    assert upload_svg.status_code == 200
    assert upload_svg.json()["logo_storage_path"].endswith(".svg")

    get_svg = client.get("/api/organizations/current/logo")
    assert get_svg.status_code == 200
    assert "image/svg+xml" in get_svg.headers["content-type"]
    assert b"<svg" in get_svg.content


def test_registration_account_types_and_organization_division(
    client: TestClient, db_session: Session
) -> None:
    # 1. Register as Government Agency
    res_gov = client.post(
        "/api/auth/register",
        json={
            "email": "stadt@freiburg.de",
            "password": "SecurePassword123!",
            "passwordConfirmation": "SecurePassword123!",
            "accountType": "government",
            "organizationName": "Stadtverwaltung Freiburg",
            "officialWebsiteUrl": "https://freiburg.de",
        },
    )
    assert res_gov.status_code == 201
    gov_data = res_gov.json()
    assert (
        gov_data.get("accountType") == "government"
        or gov_data.get("account_type") == "government"
    )
    assert (
        gov_data.get("organizationRole") == "owner"
        or gov_data.get("organization_role") == "owner"
    )
    assert (
        gov_data.get("organizationId") or gov_data.get("organization_id")
    ) is not None

    gov_org = client.get("/api/organizations/current").json()
    assert gov_org["organization_type"] == "government"
    assert gov_org["name"] == "Stadtverwaltung Freiburg"

    # 2. Register as Private Business
    client_biz = TestClient(app)
    res_biz = client_biz.post(
        "/api/auth/register",
        json={
            "email": "info@relocare.de",
            "password": "SecurePassword123!",
            "passwordConfirmation": "SecurePassword123!",
            "accountType": "business",
            "organizationName": "ReloCare Immigration GmbH",
            "officialWebsiteUrl": "https://relocare.de",
        },
    )
    assert res_biz.status_code == 201
    biz_data = res_biz.json()
    assert (
        biz_data.get("accountType") == "business"
        or biz_data.get("account_type") == "business"
    )
    assert (
        biz_data.get("organizationRole") == "owner"
        or biz_data.get("organization_role") == "owner"
    )

    biz_org = client_biz.get("/api/organizations/current").json()
    assert biz_org["organization_type"] == "business"
    assert biz_org["name"] == "ReloCare Immigration GmbH"

    # 3. Register as Individual Citizen
    client_ind = TestClient(app)
    res_ind = client_ind.post(
        "/api/auth/register",
        json={
            "email": "citizen@example.com",
            "password": "SecurePassword123!",
            "passwordConfirmation": "SecurePassword123!",
            "accountType": "individual",
        },
    )
    assert res_ind.status_code == 201
    ind_data = res_ind.json()
    assert (
        ind_data.get("accountType") == "individual"
        or ind_data.get("account_type") == "individual"
    )
