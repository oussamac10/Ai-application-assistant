"""Regression tests for the Phase 11 incorrect-export bug: PDFExportService
must never guess a PDF template for a form version that doesn't explicitly
carry one, and must never fall back to settings.PDF_TEMPLATE_KEY.
"""

import json
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import text

from app.answers.models import FormAnswer
from app.core.config import settings
from app.database.session import SessionLocal
from app.forms.models import FormField, FormTemplate, FormVersion
from app.pdf.services import PDFExportService
from app.sessions.models import FormSession
from app.sessions.security import hash_ownership_token
from app.sessions.services import ValidationError


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


@pytest.fixture
def test_fixtures_dir(tmp_path: Path) -> Path:
    pdf_dir = tmp_path / "fixtures" / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    return pdf_dir


@pytest.fixture
def mock_pdf_template(test_fixtures_dir: Path) -> Path:
    pdf_path = test_fixtures_dir / "basic-registration-v1.pdf"
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    form = c.acroForm
    form.textfield(name="first_name", x=100, y=100, width=100, height=20)
    c.showPage()
    c.save()
    return pdf_path


@pytest.fixture
def mock_pdf_mapping(test_fixtures_dir: Path) -> Path:
    mapping_path = test_fixtures_dir / "basic-registration-v1.mapping.json"
    mapping_data = {
        "templateKey": "basic-registration-v1",
        "formVersionKey": "basic-registration:1",
        "mappingVersion": 1,
        "strategy": "acroform",
        "fields": [
            {
                "fieldKey": "first_name",
                "pdfFieldName": "first_name",
                "format": "person_name",
                "maxLength": 50,
                "overflow": "truncate",
            },
        ],
    }
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(mapping_data, f)
    return mapping_path


def _make_session_for_version(
    db, version: FormVersion, field: FormField
) -> tuple[FormSession, str]:
    token = "test-token"
    session = FormSession(
        form_version_id=version.id,
        user_language="en",
        source_language="en",
        output_language="en",
        ownership_token_hash=hash_ownership_token(token),
        status="ready_for_export",
        expires_at=datetime.now(UTC) + timedelta(hours=2),
    )
    db.add(session)
    db.commit()

    ans = FormAnswer(
        session_id=session.id,
        field_id=field.id,
        original_answer="Jane",
        original_language="en",
        normalized_value="Jane",
        output_value="Jane",
        status="confirmed",
        confirmed_by_user=True,
    )
    db.add(ans)
    db.commit()
    return session, token


def test_dynamic_session_cannot_export_pdf(
    test_fixtures_dir: Path, mock_pdf_template: Path, mock_pdf_mapping: Path
) -> None:
    db = SessionLocal()
    try:
        template = FormTemplate(key="dynamic-doc-abc123", name="Dynamic form")
        db.add(template)
        db.commit()

        version = FormVersion(
            form_template_id=template.id,
            version_number=1,
            status="published",
            source_language="en",
            supported_output_languages=["en"],
            origin="dynamic_detection",
            pdf_template_key=None,
        )
        db.add(version)
        db.commit()

        field = FormField(
            form_version_id=version.id,
            key="first_name",
            field_type="string",
            required=True,
            position=0,
        )
        db.add(field)
        db.commit()

        session, token = _make_session_for_version(db, version, field)

        service = PDFExportService(db, test_fixtures_dir)
        with pytest.raises(ValidationError) as exc_info:
            service.create_export(session.public_id, token)

        assert exc_info.value.error_code == "dynamic_pdf_export_not_supported"
    finally:
        db.close()


def test_predefined_session_can_still_export_pdf(
    test_fixtures_dir: Path, mock_pdf_template: Path, mock_pdf_mapping: Path
) -> None:
    db = SessionLocal()
    try:
        template = FormTemplate(key="basic-registration", name="Basic Registration")
        db.add(template)
        db.commit()

        version = FormVersion(
            form_template_id=template.id,
            version_number=1,
            status="published",
            source_language="en",
            supported_output_languages=["en"],
            origin="predefined_template",
            pdf_template_key="basic-registration-v1",
        )
        db.add(version)
        db.commit()

        field = FormField(
            form_version_id=version.id,
            key="first_name",
            field_type="string",
            required=True,
            position=0,
        )
        db.add(field)
        db.commit()

        session, token = _make_session_for_version(db, version, field)

        service = PDFExportService(db, test_fixtures_dir)
        export = service.create_export(session.public_id, token)

        assert export.status == "completed"
        assert Path(export.storage_path).exists()
    finally:
        db.close()


def test_pdf_template_key_setting_is_never_used_as_dynamic_fallback(
    test_fixtures_dir: Path, mock_pdf_template: Path, mock_pdf_mapping: Path
) -> None:
    """Even if settings.PDF_TEMPLATE_KEY happens to point at a real mapping,
    a dynamic session must never silently use it."""
    original = settings.PDF_TEMPLATE_KEY
    settings.PDF_TEMPLATE_KEY = "basic-registration-v1"
    try:
        db = SessionLocal()
        try:
            template = FormTemplate(key="dynamic-doc-xyz", name="Dynamic form")
            db.add(template)
            db.commit()

            version = FormVersion(
                form_template_id=template.id,
                version_number=1,
                status="published",
                source_language="en",
                supported_output_languages=["en"],
                origin="dynamic_detection",
                pdf_template_key=None,
            )
            db.add(version)
            db.commit()

            field = FormField(
                form_version_id=version.id,
                key="first_name",
                field_type="string",
                required=True,
                position=0,
            )
            db.add(field)
            db.commit()

            session, token = _make_session_for_version(db, version, field)

            service = PDFExportService(db, test_fixtures_dir)
            with pytest.raises(ValidationError) as exc_info:
                service.create_export(session.public_id, token)

            assert exc_info.value.error_code == "dynamic_pdf_export_not_supported"
        finally:
            db.close()
    finally:
        settings.PDF_TEMPLATE_KEY = original
