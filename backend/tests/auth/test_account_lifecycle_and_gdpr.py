from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import fitz
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text

from app.answers.models import FormAnswer
from app.auth.email_provider import clear_mock_email_outbox, get_mock_email_outbox
from app.auth.models import AuthSession, User
from app.database.session import SessionLocal
from app.documents.models import SourceDocument
from app.forms.schemas import FieldCreate, TranslationSchema
from app.forms.services import FormService
from app.main import app
from app.pdf.models import FormExport
from app.sessions.models import FormSession
from app.storage import factory as storage_factory

PASSWORD = "correct-horse-battery"
NEW_PASSWORD = "updated-horse-battery-99"

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    client.cookies.clear()
    clear_mock_email_outbox()
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.execute(text("TRUNCATE TABLE source_documents CASCADE"))
        db.execute(text("TRUNCATE TABLE users CASCADE"))
        db.commit()
        yield
    except Exception:
        db.rollback()
    finally:
        db.close()
        client.cookies.clear()
        clear_mock_email_outbox()


def _csrf(c: TestClient) -> str:
    token = c.cookies.get("csrf_token")
    assert token
    return token


def _make_sample_pdf_bytes() -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((72, 100), "Vorname *: ________________")
    data = doc.tobytes()
    doc.close()
    return data


def _seed_published_version() -> tuple[str, str]:
    db = SessionLocal()
    try:
        service = FormService(db)
        template = service.create_template(
            key=f"gdpr-test-{uuid.uuid4().hex[:8]}", name="GDPR Test Form"
        )
        version = service.create_draft_version(
            form_template_id=template.id,
            source_language="en",
            supported_output_languages=["en"],
        )
        field = service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="first_name",
                field_type="person_name",
                required=True,
                position=1,
                question_key="personal.first_name",
                translations=[TranslationSchema(language="en", label="First Name")],
            ),
        )
        service.publish_version(version.id)
        return version.id, field.id
    finally:
        db.close()


def test_email_verification_flow_and_single_use_token() -> None:
    reg = client.post(
        "/api/auth/register",
        json={
            "email": "verify-me@example.com",
            "password": PASSWORD,
            "passwordConfirmation": PASSWORD,
        },
    )
    assert reg.status_code == 201
    assert reg.json()["emailVerified"] is False

    # Requesting a fresh verification email works and records a single-use token in mock outbox
    clear_mock_email_outbox()
    req = client.post(
        "/api/auth/verify-email/request",
        headers={"X-CSRF-Token": _csrf(client)},
    )
    assert req.status_code == 202
    outbox = get_mock_email_outbox()
    assert len(outbox) == 1
    assert outbox[0].purpose == "email_verification"
    raw_token = outbox[0].token
    assert raw_token

    # Confirm email verification
    confirm = client.post(
        "/api/auth/verify-email/confirm",
        json={"token": raw_token},
    )
    assert confirm.status_code == 200
    assert confirm.json()["emailVerified"] is True

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json()["emailVerified"] is True

    # Re-using the consumed token must fail with 422
    replay = client.post(
        "/api/auth/verify-email/confirm",
        json={"token": raw_token},
    )
    assert replay.status_code == 422
    assert replay.json()["error_code"] == "invalid_or_expired_token"


def test_password_reset_anti_enumeration_and_session_revocation() -> None:
    reg = client.post(
        "/api/auth/register",
        json={
            "email": "reset-me@example.com",
            "password": PASSWORD,
            "passwordConfirmation": PASSWORD,
        },
    )
    assert reg.status_code == 201
    old_auth_cookie = client.cookies.get("auth_session")
    assert old_auth_cookie

    clear_mock_email_outbox()

    # Unknown email must return identical 202 response and emit zero emails
    unknown = client.post(
        "/api/auth/password-reset/request",
        json={"email": "nobody-here@example.com"},
    )
    assert unknown.status_code == 202
    assert unknown.json() == {"status": "accepted"}
    assert len(get_mock_email_outbox()) == 0

    # Existing email returns identical 202 response and queues reset token
    known = client.post(
        "/api/auth/password-reset/request",
        json={"email": "Reset-Me@Example.com"},
    )
    assert known.status_code == 202
    assert known.json() == unknown.json()
    outbox = get_mock_email_outbox()
    assert len(outbox) == 1
    assert outbox[0].purpose == "password_reset"
    reset_token = outbox[0].token

    # Confirm password reset with a separate client (simulating email link click)
    reset_client = TestClient(app)
    confirm = reset_client.post(
        "/api/auth/password-reset/confirm",
        json={
            "token": reset_token,
            "password": NEW_PASSWORD,
            "passwordConfirmation": NEW_PASSWORD,
        },
    )
    assert confirm.status_code == 200
    assert confirm.json() == {"status": "password_reset"}

    # Replaying reset token fails
    replay = reset_client.post(
        "/api/auth/password-reset/confirm",
        json={
            "token": reset_token,
            "password": NEW_PASSWORD,
            "passwordConfirmation": NEW_PASSWORD,
        },
    )
    assert replay.status_code == 422
    assert replay.json()["error_code"] == "invalid_or_expired_token"

    # Existing logged-in session cookie must now be revoked!
    stale_me = client.get("/api/auth/me")
    assert stale_me.status_code == 401

    # Old password fails; new password succeeds
    old_login = reset_client.post(
        "/api/auth/login",
        json={"email": "reset-me@example.com", "password": PASSWORD},
    )
    assert old_login.status_code == 401

    new_login = reset_client.post(
        "/api/auth/login",
        json={"email": "reset-me@example.com", "password": NEW_PASSWORD},
    )
    assert new_login.status_code == 200


def test_delete_application_hard_deletes_db_rows_and_storage_blobs(
    tmp_path: pytest.TempPathFactory,
) -> None:
    version_id, field_id = _seed_published_version()

    reg = client.post(
        "/api/auth/register",
        json={
            "email": "app-eraser@example.com",
            "password": PASSWORD,
            "passwordConfirmation": PASSWORD,
        },
    )
    assert reg.status_code == 201
    user_id = reg.json()["id"]
    csrf = _csrf(client)

    # Upload a source document as the authenticated user
    upload = client.post(
        "/api/source-documents",
        files={"file": ("form.pdf", _make_sample_pdf_bytes(), "application/pdf")},
        data={"language": "en", "privacyAccepted": "true"},
        headers={"X-CSRF-Token": csrf},
    )
    assert upload.status_code == 201
    doc_public_id = upload.json()["documentId"]

    # Create an owned session bound to that source document, an answer, and an export blob
    staged_export = tmp_path / "staged-export.pdf"  # type: ignore[operator]
    staged_export.write_bytes(_make_sample_pdf_bytes())
    provider = storage_factory.get_storage_provider()
    export_ref = provider.save_file(
        namespace="exports",
        filename=f"{uuid.uuid4()}.pdf",
        source_path=staged_export,
        content_type="application/pdf",
    )

    db = SessionLocal()
    try:
        doc = db.scalars(
            select(SourceDocument).where(SourceDocument.public_id == doc_public_id)
        ).first()
        assert doc is not None
        doc_storage_path = doc.storage_path
        assert provider.exists(doc_storage_path)
        assert provider.exists(export_ref)

        now = datetime.now(UTC)
        session = FormSession(
            user_id=user_id,
            source_document_id=doc.id,
            form_version_id=version_id,
            user_language="en",
            source_language="en",
            output_language="en",
            status="in_progress",
            total_required_fields=1,
            expires_at=now + timedelta(hours=24),
        )
        db.add(session)
        db.flush()
        session_public_id = session.public_id
        session_internal_id = session.id

        ans = FormAnswer(
            session_id=session.id,
            field_id=field_id,
            original_answer="Amina",
            original_language="en",
            normalized_value={"fullName": "Amina"},
            output_value="Amina",
            status="confirmed",
            validation_status="valid",
            confirmed_by_user=True,
        )
        export = FormExport(
            session_id=session.id,
            form_version_id=version_id,
            template_key="test-template",
            mapping_version=1,
            status="completed",
            file_name="export.pdf",
            storage_path=export_ref,
            content_type="application/pdf",
            file_size=128,
            created_at=now,
            expires_at=now + timedelta(hours=24),
        )
        db.add_all([ans, export])
        db.commit()
    finally:
        db.close()

    res = client.delete(
        f"/api/applications/{session_public_id}",
        headers={"X-CSRF-Token": csrf},
    )
    assert res.status_code == 204

    # Verify DB rows AND storage blobs are completely gone
    assert not provider.exists(export_ref)
    assert not provider.exists(doc_storage_path)

    db = SessionLocal()
    try:
        assert db.get(FormSession, session_internal_id) is None
        assert (
            db.scalars(
                select(FormAnswer).where(FormAnswer.session_id == session_internal_id)
            ).first()
            is None
        )
        assert (
            db.scalars(
                select(FormExport).where(FormExport.session_id == session_internal_id)
            ).first()
            is None
        )
        assert (
            db.scalars(
                select(SourceDocument).where(SourceDocument.public_id == doc_public_id)
            ).first()
            is None
        )
    finally:
        db.close()


def test_gdpr_export_and_delete_account_purges_all_user_data_and_blobs(
    tmp_path: pytest.TempPathFactory,
) -> None:
    version_id, field_id = _seed_published_version()

    reg = client.post(
        "/api/auth/register",
        json={
            "email": "gdpr-owner@example.com",
            "password": PASSWORD,
            "passwordConfirmation": PASSWORD,
        },
    )
    assert reg.status_code == 201
    user_id = reg.json()["id"]
    csrf = _csrf(client)

    upload = client.post(
        "/api/source-documents",
        files={"file": ("anmeldung.pdf", _make_sample_pdf_bytes(), "application/pdf")},
        data={"language": "en", "privacyAccepted": "true"},
        headers={"X-CSRF-Token": csrf},
    )
    assert upload.status_code == 201
    doc_public_id = upload.json()["documentId"]

    staged_export = tmp_path / "staged-export-2.pdf"  # type: ignore[operator]
    staged_export.write_bytes(_make_sample_pdf_bytes())
    provider = storage_factory.get_storage_provider()
    export_ref = provider.save_file(
        namespace="exports",
        filename=f"{uuid.uuid4()}.pdf",
        source_path=staged_export,
        content_type="application/pdf",
    )

    db = SessionLocal()
    try:
        doc = db.scalars(
            select(SourceDocument).where(SourceDocument.public_id == doc_public_id)
        ).first()
        assert doc is not None
        doc_storage_path = doc.storage_path

        now = datetime.now(UTC)
        session = FormSession(
            user_id=user_id,
            source_document_id=doc.id,
            title="Berlin Anmeldung",
            form_version_id=version_id,
            user_language="en",
            source_language="de",
            output_language="de",
            status="completed",
            total_required_fields=1,
            expires_at=now + timedelta(hours=24),
        )
        db.add(session)
        db.flush()

        db.add(
            FormAnswer(
                session_id=session.id,
                field_id=field_id,
                original_answer="Tariq",
                original_language="en",
                normalized_value={"fullName": "Tariq"},
                output_value="Tariq",
                status="confirmed",
                validation_status="valid",
                confirmed_by_user=True,
            )
        )
        db.add(
            FormExport(
                session_id=session.id,
                form_version_id=version_id,
                template_key="test-template",
                mapping_version=1,
                status="completed",
                file_name="anmeldung_filled.pdf",
                storage_path=export_ref,
                content_type="application/pdf",
                file_size=256,
                created_at=now,
                expires_at=now + timedelta(hours=24),
            )
        )
        db.commit()
    finally:
        db.close()

    # 1. GDPR Art. 20 Data Export
    exported = client.get("/api/auth/me/export")
    assert exported.status_code == 200
    assert "no-store" in exported.headers.get("cache-control", "").lower()
    payload = exported.json()
    serialized = str(payload)
    assert "password_hash" not in serialized
    assert "passwordHash" not in serialized
    assert "storage_path" not in serialized
    assert "storagePath" not in serialized
    assert payload["account"]["email"] == "gdpr-owner@example.com"
    assert len(payload["applications"]) == 1
    assert payload["applications"][0]["title"] == "Berlin Anmeldung"
    assert payload["applications"][0]["answers"][0]["originalAnswer"] == "Tariq"
    assert len(payload["documents"]) == 1
    assert payload["documents"][0]["originalFilename"] == "anmeldung.pdf"

    # 2. GDPR Art. 17 Delete Account requires CSRF
    no_csrf = client.delete("/api/auth/me")
    assert no_csrf.status_code == 401

    deleted = client.delete("/api/auth/me", headers={"X-CSRF-Token": csrf})
    assert deleted.status_code == 204

    assert not provider.exists(doc_storage_path)
    assert not provider.exists(export_ref)

    db = SessionLocal()
    try:
        assert db.get(User, user_id) is None
        assert (
            db.scalars(select(AuthSession).where(AuthSession.user_id == user_id)).all()
            == []
        )
        assert (
            db.scalars(select(FormSession).where(FormSession.user_id == user_id)).all()
            == []
        )
        assert db.scalars(select(FormAnswer)).all() == []
        assert (
            db.scalars(
                select(SourceDocument).where(SourceDocument.user_id == user_id)
            ).all()
            == []
        )
    finally:
        db.close()
