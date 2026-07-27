from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database.session import SessionLocal
from app.forms.schemas import FieldCreate, TranslationSchema
from app.forms.services import FormService
from app.main import app

REGISTER_PASSWORD = "correct-horse-battery"

# Two independent clients so two-user (claim-conflict/IDOR) tests never share
# cookies. A single shared TestClient(app), entered once for the whole
# module rather than per-test, mirrors the existing test_sessions.py pattern
# and avoids repeatedly tearing down/rebuilding the ASGI lifespan (which was
# observed to leave the shared SQLAlchemy connection pool in a bad state).
client = TestClient(app)
other_client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    client.cookies.clear()
    other_client.cookies.clear()
    db = SessionLocal()
    try:
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


@pytest.fixture
def published_form_version() -> Generator[str, None, None]:
    db = SessionLocal()
    try:
        service = FormService(db)
        template = service.create_template(
            key="claim-test-form", name="Claim Test Form"
        )
        version = service.create_draft_version(
            form_template_id=template.id,
            source_language="en",
            supported_output_languages=["en"],
        )
        service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="first_name",
                field_type="person_name",
                required=True,
                position=1,
                translations=[TranslationSchema(language="en", label="First Name")],
            ),
        )
        service.publish_version(version.id)
        yield version.id
    finally:
        db.close()


def _register(c: TestClient, email: str = "owner@example.com") -> None:
    response = c.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": REGISTER_PASSWORD,
            "passwordConfirmation": REGISTER_PASSWORD,
        },
    )
    assert response.status_code == 201


def _csrf(c: TestClient) -> str:
    token = c.cookies.get("csrf_token")
    assert token
    return token


def _create_anonymous_session(c: TestClient, form_version_id: str) -> tuple[str, str]:
    response = c.post(
        f"/api/form-versions/{form_version_id}/sessions",
        json={"userLanguage": "en", "outputLanguage": "en"},
    )
    assert response.status_code == 201
    data = response.json()
    return data["sessionId"], data["ownershipToken"]


def test_list_applications_empty_when_unauthenticated() -> None:
    response = client.get("/api/applications")
    assert response.status_code == 401


def test_claim_then_appears_in_history_and_resumable(
    published_form_version: str,
) -> None:
    session_id, token = _create_anonymous_session(client, published_form_version)

    _register(client)
    claim = client.post(
        "/api/applications/claim",
        json={"sessionId": session_id, "sessionToken": token},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert claim.status_code == 200
    assert claim.json()["id"] == session_id

    listing = client.get("/api/applications")
    assert listing.status_code == 200
    ids = [item["id"] for item in listing.json()]
    assert session_id in ids

    # The old anonymous token must no longer authorize access, even for a
    # caller with no auth cookie at all.
    anonymous_caller = TestClient(app)
    anon_check = anonymous_caller.get(
        f"/api/form-sessions/{session_id}", headers={"X-Session-Token": token}
    )
    assert anon_check.status_code == 401

    # But the authenticated cookie session can resume it directly.
    resumed = client.get(f"/api/form-sessions/{session_id}")
    assert resumed.status_code == 200


def test_claim_is_idempotent_for_same_user(published_form_version: str) -> None:
    session_id, token = _create_anonymous_session(client, published_form_version)
    _register(client)
    csrf = _csrf(client)

    first = client.post(
        "/api/applications/claim",
        json={"sessionId": session_id, "sessionToken": token},
        headers={"X-CSRF-Token": csrf},
    )
    assert first.status_code == 200

    second = client.post(
        "/api/applications/claim",
        json={"sessionId": session_id, "sessionToken": token},
        headers={"X-CSRF-Token": csrf},
    )
    assert second.status_code == 200
    assert second.json()["id"] == session_id


def test_claim_rejects_invalid_token(published_form_version: str) -> None:
    session_id, _token = _create_anonymous_session(client, published_form_version)
    _register(client)

    response = client.post(
        "/api/applications/claim",
        json={"sessionId": session_id, "sessionToken": "wrong-token"},
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert response.status_code == 401


def test_claim_by_second_user_rejected(published_form_version: str) -> None:
    session_id, token = _create_anonymous_session(client, published_form_version)
    _register(client, email="first@example.com")
    csrf = _csrf(client)
    claimed = client.post(
        "/api/applications/claim",
        json={"sessionId": session_id, "sessionToken": token},
        headers={"X-CSRF-Token": csrf},
    )
    assert claimed.status_code == 200

    _register(other_client, email="second@example.com")
    other_csrf = _csrf(other_client)
    rejected = other_client.post(
        "/api/applications/claim",
        json={"sessionId": session_id, "sessionToken": token},
        headers={"X-CSRF-Token": other_csrf},
    )
    assert rejected.status_code == 401


def test_rename_and_delete_application(published_form_version: str) -> None:
    session_id, token = _create_anonymous_session(client, published_form_version)
    _register(client)
    csrf = _csrf(client)
    client.post(
        "/api/applications/claim",
        json={"sessionId": session_id, "sessionToken": token},
        headers={"X-CSRF-Token": csrf},
    )

    rename = client.patch(
        f"/api/applications/{session_id}",
        json={"title": "My Visa Application"},
        headers={"X-CSRF-Token": csrf},
    )
    assert rename.status_code == 200
    assert rename.json()["title"] == "My Visa Application"

    empty_title = client.patch(
        f"/api/applications/{session_id}",
        json={"title": "   "},
        headers={"X-CSRF-Token": csrf},
    )
    assert empty_title.status_code == 422

    delete = client.delete(
        f"/api/applications/{session_id}", headers={"X-CSRF-Token": csrf}
    )
    assert delete.status_code == 204

    listing = client.get("/api/applications")
    assert session_id not in [item["id"] for item in listing.json()]

    detail = client.get(f"/api/applications/{session_id}")
    assert detail.status_code == 404


def test_application_not_visible_to_other_user(published_form_version: str) -> None:
    session_id, token = _create_anonymous_session(client, published_form_version)
    _register(client, email="owner-a@example.com")
    csrf = _csrf(client)
    client.post(
        "/api/applications/claim",
        json={"sessionId": session_id, "sessionToken": token},
        headers={"X-CSRF-Token": csrf},
    )

    _register(other_client, email="owner-b@example.com")
    detail = other_client.get(f"/api/applications/{session_id}")
    assert detail.status_code == 404
    listing = other_client.get("/api/applications")
    assert listing.json() == []
