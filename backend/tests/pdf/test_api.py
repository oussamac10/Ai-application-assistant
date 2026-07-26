from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.answers.models import FormAnswer
from app.database.session import SessionLocal
from app.forms.models import FormField, FormTemplate, FormVersion
from app.main import app
from app.pdf.models import FormExport
from app.sessions.models import FormSession
from app.sessions.security import hash_ownership_token


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.execute(text("TRUNCATE TABLE form_exports CASCADE"))
        db.commit()
        yield
    except Exception:
        db.rollback()
    finally:
        db.close()


def test_pdf_api_endpoints_flow(client: TestClient) -> None:
    db_session = SessionLocal()
    try:
        # Setup template and versions
        template = FormTemplate(key="basic-registration", name="Basic Registration")
        db_session.add(template)
        db_session.commit()

        version = FormVersion(
            form_template_id=template.id,
            version_number=1,
            status="published",
            source_language="en",
            supported_output_languages=["en", "de", "ar"],
            pdf_template_key="basic-registration-v1",
        )
        db_session.add(version)
        db_session.commit()

        field = FormField(
            form_version_id=version.id,
            key="first_name",
            field_type="person_name",
            required=True,
            position=1,
        )
        db_session.add(field)
        db_session.commit()

        token = "owner-secret-token"
        token_hash = hash_ownership_token(token)
        session = FormSession(
            form_version_id=version.id,
            user_language="en",
            source_language="en",
            output_language="en",
            ownership_token_hash=token_hash,
            status="ready_for_export",
            expires_at=datetime.now(UTC) + timedelta(hours=2),
        )
        db_session.add(session)
        db_session.commit()

        ans = FormAnswer(
            session_id=session.id,
            field_id=field.id,
            original_answer="Yusuf",
            original_language="en",
            normalized_value="Yusuf",
            output_value="Yusuf",
            status="confirmed",
            confirmed_by_user=True,
        )
        db_session.add(ans)
        db_session.commit()

        # 1. POST /api/form-sessions/{session_id}/exports (Valid request)
        response = client.post(
            f"/api/form-sessions/{session.public_id}/exports",
            headers={"X-Session-Token": token},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "downloadUrl" in data
        export_public_id = data["exportId"]

        # 2. GET /api/form-exports/{export_id}/download (Valid request)
        download_res = client.get(
            f"/api/form-exports/{export_public_id}/download",
            headers={"X-Session-Token": token},
        )
        assert download_res.status_code == 200
        assert download_res.headers["content-type"] == "application/pdf"
        assert "attachment" in download_res.headers["content-disposition"]

        # 3. GET download (Unauthorized request - wrong token)
        unauth_res = client.get(
            f"/api/form-exports/{export_public_id}/download",
            headers={"X-Session-Token": "bad-token"},
        )
        assert unauth_res.status_code == 401

        # 4. GET download (Expired export error)
        # Fetch export and update expires_at to past
        export_record = (
            db_session.query(FormExport).filter_by(public_id=export_public_id).first()
        )
        assert export_record is not None
        export_record.created_at = datetime.now(UTC) - timedelta(days=2)
        export_record.expires_at = datetime.now(UTC) - timedelta(days=1)
        db_session.commit()

        expired_res = client.get(
            f"/api/form-exports/{export_public_id}/download",
            headers={"X-Session-Token": token},
        )
        assert expired_res.status_code == 422
        assert "expired" in expired_res.json()["detail"].lower()
    finally:
        db_session.close()
