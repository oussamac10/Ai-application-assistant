from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database.session import SessionLocal
from app.forms.models import FormVersion
from app.forms.schemas import FieldCreate, TranslationSchema
from app.forms.services import FormService
from app.main import app
from app.sessions.models import FormSession
from app.sessions.services import SessionService

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.commit()
        yield
    except Exception:
        db.rollback()
    finally:
        db.close()


@pytest.fixture
def form_versions() -> dict[str, str]:
    db = SessionLocal()
    service = FormService(db)

    # 1. Create published template and version
    pub_template = service.create_template(key="published-form", name="Published Form")
    pub_ver = service.create_draft_version(
        form_template_id=pub_template.id,
        source_language="en",
        supported_output_languages=["en", "de", "ar"],
    )
    # Add a required field
    service.add_field_to_draft(
        pub_ver.id,
        FieldCreate(
            key="first_name",
            field_type="person_name",
            required=True,
            position=1,
            translations=[TranslationSchema(language="en", label="First Name")],
        ),
    )
    # Add an optional field
    service.add_field_to_draft(
        pub_ver.id,
        FieldCreate(
            key="middle_name",
            field_type="string",
            required=False,
            position=2,
            translations=[TranslationSchema(language="en", label="Middle Name")],
        ),
    )
    # Publish it
    service.publish_version(pub_ver.id)

    # 2. Create draft template and version
    draft_template = service.create_template(key="draft-form", name="Draft Form")
    draft_ver = service.create_draft_version(
        form_template_id=draft_template.id,
        source_language="en",
        supported_output_languages=["en"],
    )

    # 3. Create archived template and version
    archived_template = service.create_template(
        key="archived-form", name="Archived Form"
    )
    archived_ver = service.create_draft_version(
        form_template_id=archived_template.id,
        source_language="en",
        supported_output_languages=["en"],
    )
    # Set status directly in DB to archived
    db_archived_ver = db.get(FormVersion, archived_ver.id)
    assert db_archived_ver is not None
    db_archived_ver.status = "archived"
    db.commit()

    pub_ver_id = pub_ver.id
    draft_ver_id = draft_ver.id
    archived_ver_id = archived_ver.id

    db.close()

    return {
        "published": pub_ver_id,
        "draft": draft_ver_id,
        "archived": archived_ver_id,
    }


def test_create_session_success(form_versions: dict[str, str]) -> None:
    pub_id = form_versions["published"]
    response = client.post(
        f"/api/form-versions/{pub_id}/sessions",
        json={"userLanguage": "ar", "outputLanguage": "de"},
    )
    assert response.status_code == 201
    data = response.json()

    assert "sessionId" in data
    assert "ownershipToken" in data
    assert data["status"] == "session_created"
    assert data["sourceLanguage"] == "en"
    assert data["userLanguage"] == "ar"
    assert data["outputLanguage"] == "de"
    assert data["currentFieldPosition"] == 0
    # There is 1 required field ("first_name" is required, "middle_name" is optional)
    assert data["totalRequiredFields"] == 1
    assert "expiresAt" in data

    # Verify that raw token is not stored in DB (we query db directly to check)
    db = SessionLocal()
    db_sess = db.query(FormSession).filter_by(public_id=data["sessionId"]).first()
    assert db_sess is not None
    assert db_sess.ownership_token_hash != data["ownershipToken"]
    db.close()


def test_create_session_rejection(form_versions: dict[str, str]) -> None:
    # 1. Reject draft version
    draft_id = form_versions["draft"]
    response = client.post(
        f"/api/form-versions/{draft_id}/sessions",
        json={"userLanguage": "en", "outputLanguage": "en"},
    )
    assert response.status_code == 409

    # 2. Reject archived version
    arch_id = form_versions["archived"]
    response2 = client.post(
        f"/api/form-versions/{arch_id}/sessions",
        json={"userLanguage": "en", "outputLanguage": "en"},
    )
    assert response2.status_code == 409

    # 3. Reject invalid user language
    pub_id = form_versions["published"]
    response3 = client.post(
        f"/api/form-versions/{pub_id}/sessions",
        json={"userLanguage": "invalid-lang", "outputLanguage": "en"},
    )
    assert response3.status_code == 422

    # 4. Reject unsupported output language
    response4 = client.post(
        f"/api/form-versions/{pub_id}/sessions",
        json={"userLanguage": "de", "outputLanguage": "fr"},
    )
    assert response4.status_code == 422


def test_read_session(form_versions: dict[str, str]) -> None:
    pub_id = form_versions["published"]
    res_create = client.post(
        f"/api/form-versions/{pub_id}/sessions",
        json={"userLanguage": "ar", "outputLanguage": "de"},
    )
    sess_id = res_create.json()["sessionId"]
    token = res_create.json()["ownershipToken"]

    # 1. Read with valid token
    response = client.get(
        f"/api/form-sessions/{sess_id}",
        headers={"X-Session-Token": token},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["sessionId"] == sess_id
    assert data["status"] == "session_created"
    assert data["progressPercentage"] == 0
    assert "ownershipToken" not in data
    assert "ownership_token_hash" not in data

    # 2. Reject missing token
    response_missing = client.get(f"/api/form-sessions/{sess_id}")
    assert response_missing.status_code == 401
    assert response_missing.json()["detail"] == "Invalid session credentials"

    # 3. Reject invalid token
    response_invalid = client.get(
        f"/api/form-sessions/{sess_id}",
        headers={"X-Session-Token": "wrong-token"},
    )
    assert response_invalid.status_code == 401
    assert response_invalid.json()["detail"] == "Invalid session credentials"

    # 4. Reject and do not leak session existence on wrong token
    response_leak = client.get(
        "/api/form-sessions/non-existent-uuid",
        headers={"X-Session-Token": "wrong-token"},
    )
    assert response_leak.status_code == 401
    assert response_leak.json()["detail"] == "Invalid session credentials"


def test_start_session(form_versions: dict[str, str]) -> None:
    pub_id = form_versions["published"]
    res_create = client.post(
        f"/api/form-versions/{pub_id}/sessions",
        json={"userLanguage": "en", "outputLanguage": "en"},
    )
    sess_id = res_create.json()["sessionId"]
    token = res_create.json()["ownershipToken"]

    # Start session successfully
    response = client.post(
        f"/api/form-sessions/{sess_id}/start",
        headers={"X-Session-Token": token},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"

    # Reject starting an already started session (Conflict)
    response_started = client.post(
        f"/api/form-sessions/{sess_id}/start",
        headers={"X-Session-Token": token},
    )
    assert response_started.status_code == 409


def test_cancel_session(form_versions: dict[str, str]) -> None:
    pub_id = form_versions["published"]
    res_create = client.post(
        f"/api/form-versions/{pub_id}/sessions",
        json={"userLanguage": "en", "outputLanguage": "en"},
    )
    sess_id = res_create.json()["sessionId"]
    token = res_create.json()["ownershipToken"]

    # Cancel session from created state
    response = client.post(
        f"/api/form-sessions/{sess_id}/cancel",
        headers={"X-Session-Token": token},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"

    # Reject cancelling already cancelled session
    response_cancelled = client.post(
        f"/api/form-sessions/{sess_id}/cancel",
        headers={"X-Session-Token": token},
    )
    assert response_cancelled.status_code == 409


def test_session_expiration(form_versions: dict[str, str]) -> None:
    db = SessionLocal()
    try:
        service = SessionService(db)
        pub_id = form_versions["published"]
        # Create session directly via service to manipulate expires_at
        session, token = service.create_session(
            form_version_id=pub_id,
            user_language="en",
            output_language="en",
        )
        db.commit()

        # Manipulate expiration date in DB to past
        db_sess = db.query(FormSession).filter_by(id=session.id).first()
        assert db_sess is not None
        db_sess.expires_at = datetime.now(UTC) - timedelta(minutes=10)
        db.commit()

        # Accessing session should mark it as expired
        response = client.get(
            f"/api/form-sessions/{session.public_id}",
            headers={"X-Session-Token": token},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "expired"

        # Expired session cannot be started
        res_start = client.post(
            f"/api/form-sessions/{session.public_id}/start",
            headers={"X-Session-Token": token},
        )
        assert res_start.status_code == 409

        # Expired session cannot be cancelled
        res_cancel = client.post(
            f"/api/form-sessions/{session.public_id}/cancel",
            headers={"X-Session-Token": token},
        )
        assert res_cancel.status_code == 409
    finally:
        db.close()


def test_cleanup_expired_sessions_command(form_versions: dict[str, str]) -> None:
    db = SessionLocal()
    try:
        service = SessionService(db)
        pub_id = form_versions["published"]

        # Create two sessions
        sess1, tok1 = service.create_session(
            pub_id, user_language="en", output_language="en"
        )
        sess2, tok2 = service.create_session(
            pub_id, user_language="en", output_language="en"
        )
        db.commit()

        # 1. Backdate expires_at for sess1
        db_sess1 = db.query(FormSession).filter_by(id=sess1.id).first()
        assert db_sess1 is not None
        db_sess1.expires_at = datetime.now(UTC) - timedelta(minutes=10)

        # 2. Backdate expires_at for sess2 but cancel it first
        db_sess2 = db.query(FormSession).filter_by(id=sess2.id).first()
        assert db_sess2 is not None
        db_sess2.expires_at = datetime.now(UTC) - timedelta(minutes=10)
        db_sess2.status = "cancelled"

        db.commit()

        # Run cleanup
        count = service.cleanup_expired_sessions()
        # Only sess1 should be cleaned up (sess2 is cancelled, which is terminal)
        assert count == 1

        # Verify sess1 status in DB
        db.refresh(db_sess1)
        assert db_sess1.status == "expired"
    finally:
        db.close()
