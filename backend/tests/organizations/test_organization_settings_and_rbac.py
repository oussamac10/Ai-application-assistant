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
