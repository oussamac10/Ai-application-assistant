"""Phase S0 security, privacy, and production hardening regression tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import fitz
import pytest
from pypdf import PdfReader
from sqlalchemy import text

from app.applications.services import to_summary_dict
from app.auth.errors import AuthUnauthorizedError
from app.auth.services import _DUMMY_PASSWORD_HASH, AuthService
from app.commands.cleanup_expired_exports import cleanup_expired_exports
from app.core.config import Settings
from app.database.session import SessionLocal
from app.documents.models import SourceDocument
from app.forms.schemas import FieldCreate, TranslationSchema
from app.forms.services import FormService
from app.pdf.renderers.pypdf_renderer import PypdfRenderer
from app.pdf.schemas import PDFFieldMapping, PDFTemplateMapping
from app.sessions.services import SessionService, UnauthorizedError


def test_production_settings_fail_fast_on_weak_or_missing_secrets() -> None:
    strong_session = "s" * 40
    strong_auth = "a" * 40

    # Missing SESSION_TOKEN_SECRET in production must raise
    with pytest.raises(ValueError, match="SESSION_TOKEN_SECRET"):
        Settings(
            _env_file=None,
            ENVIRONMENT="production",
            SESSION_TOKEN_SECRET="",
            AUTH_SECRET=strong_auth,
            AUTH_COOKIE_SECURE=True,
        )

    # Dev fallback SESSION_TOKEN_SECRET in production must raise
    with pytest.raises(ValueError, match="SESSION_TOKEN_SECRET"):
        Settings(
            _env_file=None,
            ENVIRONMENT="production",
            SESSION_TOKEN_SECRET="unsafe-dev-fallback-secret-key-12345678",
            AUTH_SECRET=strong_auth,
            AUTH_COOKIE_SECURE=True,
        )

    # Missing/short AUTH_SECRET in production must raise
    with pytest.raises(ValueError, match="AUTH_SECRET"):
        Settings(
            _env_file=None,
            ENVIRONMENT="production",
            SESSION_TOKEN_SECRET=strong_session,
            AUTH_SECRET="too-short",
            AUTH_COOKIE_SECURE=True,
        )

    # AUTH_COOKIE_SECURE=False in production must raise
    with pytest.raises(ValueError, match="AUTH_COOKIE_SECURE"):
        Settings(
            _env_file=None,
            ENVIRONMENT="production",
            SESSION_TOKEN_SECRET=strong_session,
            AUTH_SECRET=strong_auth,
            AUTH_COOKIE_SECURE=False,
        )

    # Valid production configuration succeeds
    valid = Settings(
        _env_file=None,
        ENVIRONMENT="production",
        SESSION_TOKEN_SECRET=strong_session,
        AUTH_SECRET=strong_auth,
        AUTH_COOKIE_SECURE=True,
    )
    assert valid.is_production is True


def test_login_runs_dummy_argon2_verification_for_unknown_email() -> None:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE users CASCADE"))
        db.commit()
        service = AuthService(db)

        with patch("app.auth.services.verify_password") as mock_verify:
            mock_verify.return_value = False
            with pytest.raises(AuthUnauthorizedError):
                service.login("nonexistent-account@example.com", "any-password-123")

            mock_verify.assert_called_once_with(
                "any-password-123", _DUMMY_PASSWORD_HASH
            )
    finally:
        db.close()


def test_rebind_on_next_request_sentinel_is_rejected() -> None:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.commit()

        form_svc = FormService(db)
        tpl = form_svc.create_template(key="rebind-test", name="Rebind Test")
        ver = form_svc.create_draft_version(
            form_template_id=tpl.id,
            source_language="en",
            supported_output_languages=["en"],
        )
        form_svc.add_field_to_draft(
            ver.id,
            FieldCreate(
                key="full_name",
                field_type="string",
                required=True,
                position=1,
                translations=[TranslationSchema(language="en", label="Full Name")],
            ),
        )
        form_svc.publish_version(ver.id)

        session_svc = SessionService(db)
        session, _valid_token = session_svc.create_session(
            form_version_id=ver.id,
            user_language="en",
            output_language="en",
        )
        # Simulate legacy sentinel row in DB
        session.ownership_token_hash = "REBIND_ON_NEXT_REQUEST"
        db.commit()

        with pytest.raises(UnauthorizedError):
            session_svc.get_session(session.public_id, "attacker-chosen-token")
    finally:
        db.close()


def test_cleanup_preserves_claimed_user_documents_and_purges_anonymous(
    tmp_path: Path,
) -> None:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE source_documents CASCADE"))
        db.execute(text("TRUNCATE TABLE users CASCADE"))
        db.commit()

        auth_svc = AuthService(db)
        owner = auth_svc.register(
            "claimed-owner@example.com",
            "strong-owner-pass-123",
            "strong-owner-pass-123",
        )

        anon_file = tmp_path / "anon_expired.pdf"
        anon_file.write_bytes(b"%PDF-1.4\n%anon")
        claimed_file = tmp_path / "claimed_past_ttl.pdf"
        claimed_file.write_bytes(b"%PDF-1.4\n%claimed")

        past = datetime.now(UTC) - timedelta(hours=48)
        anon_doc = SourceDocument(
            user_id=None,
            ownership_token_hash="a" * 64,
            original_filename="anon.pdf",
            sanitized_filename="anon.pdf",
            storage_path=str(anon_file),
            content_type="application/pdf",
            size_bytes=15,
            checksum_sha256="1" * 64,
            status="analyzed",
            expires_at=past,
        )
        claimed_doc = SourceDocument(
            user_id=owner.id,
            ownership_token_hash=None,
            original_filename="claimed.pdf",
            sanitized_filename="claimed.pdf",
            storage_path=str(claimed_file),
            content_type="application/pdf",
            size_bytes=18,
            checksum_sha256="2" * 64,
            status="analyzed",
            expires_at=past,
        )
        db.add_all([anon_doc, claimed_doc])
        db.commit()
        anon_id = anon_doc.id
        claimed_id = claimed_doc.id
    finally:
        db.close()

    exit_code = cleanup_expired_exports()
    assert exit_code == 0

    assert not anon_file.exists()
    assert claimed_file.exists()

    verify_db = SessionLocal()
    try:
        refreshed_anon = verify_db.get(SourceDocument, anon_id)
        refreshed_claimed = verify_db.get(SourceDocument, claimed_id)
        assert refreshed_anon is not None and refreshed_anon.status == "deleted"
        assert refreshed_claimed is not None and refreshed_claimed.status == "analyzed"
    finally:
        verify_db.close()


def test_pypdf_renderer_fills_acroform_fields_across_multiple_pages(
    tmp_path: Path,
) -> None:
    template_pdf = tmp_path / "two_page_acroform.pdf"
    output_pdf = tmp_path / "two_page_filled.pdf"

    doc = fitz.open()
    page1 = doc.new_page(width=595, height=842)
    w1 = fitz.Widget()
    w1.field_name = "page1_first_name"
    w1.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    w1.rect = fitz.Rect(100, 100, 300, 130)
    page1.add_widget(w1)

    page2 = doc.new_page(width=595, height=842)
    w2 = fitz.Widget()
    w2.field_name = "page2_city"
    w2.field_type = fitz.PDF_WIDGET_TYPE_TEXT
    w2.rect = fitz.Rect(100, 200, 300, 230)
    page2.add_widget(w2)

    doc.save(template_pdf)
    doc.close()

    mapping = PDFTemplateMapping(
        templateKey="two-page-test",
        formVersionKey="two-page:1",
        mappingVersion=1,
        strategy="acroform",
        fields=[
            PDFFieldMapping(
                fieldKey="first_name",
                pdfFieldName="page1_first_name",
                format="text",
                page=1,
            ),
            PDFFieldMapping(
                fieldKey="city",
                pdfFieldName="page2_city",
                format="text",
                page=2,
            ),
        ],
    )

    renderer = PypdfRenderer()
    res = renderer.render(
        template_path=template_pdf,
        output_path=output_pdf,
        mapping=mapping,
        values={"first_name": "Youssef", "city": "Frankfurt am Main"},
    )
    assert res.page_count == 2

    reader = PdfReader(output_pdf)
    fields = reader.get_form_text_fields()
    assert fields.get("page1_first_name") == "Youssef"
    assert fields.get("page2_city") == "Frankfurt am Main"


def test_application_progress_uses_total_fields_when_required_count_is_zero() -> None:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE source_documents CASCADE"))
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.commit()

        doc = SourceDocument(
            user_id=None,
            ownership_token_hash="c" * 64,
            original_filename="dyn.pdf",
            sanitized_filename="dyn.pdf",
            storage_path="/tmp/dyn.pdf",
            content_type="application/pdf",
            size_bytes=10,
            checksum_sha256="3" * 64,
            status="analyzed",
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        db.add(doc)
        db.commit()

        form_svc = FormService(db)
        tpl = form_svc.create_template(key="dyn-progress-2", name="Dynamic Progress 2")
        ver = form_svc.create_draft_version(
            form_template_id=tpl.id,
            source_language="de",
            supported_output_languages=["de"],
            origin="dynamic_detection",
        )
        for idx in range(1, 5):
            form_svc.add_field_to_draft(
                ver.id,
                FieldCreate(
                    key=f"f_{idx}",
                    field_type="string",
                    required=False,
                    requiredness="unknown",
                    position=idx,
                    translations=[
                        TranslationSchema(language="de", label=f"Feld {idx}")
                    ],
                ),
            )
        form_svc.publish_version(ver.id)

        session_svc = SessionService(db)
        session, _ = session_svc.create_session(
            form_version_id=ver.id,
            user_language="en",
            output_language="de",
            source_document_id=doc.id,
        )
        assert session.total_required_fields == 0
        session.current_field_position = 2
        db.commit()
        db.refresh(session)

        summary = to_summary_dict(session)
        assert summary["progress_percentage"] == 50

        session.status = "completed"
        assert to_summary_dict(session)["progress_percentage"] == 100
    finally:
        db.close()
