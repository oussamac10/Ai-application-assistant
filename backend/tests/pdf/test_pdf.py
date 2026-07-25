import json
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import text

from app.answers.models import FormAnswer
from app.database.session import SessionLocal
from app.forms.models import FormField, FormTemplate, FormVersion
from app.pdf.formatting import format_field_value
from app.pdf.registry import PDFMappingError, PDFMappingLoader, PDFTemplateRegistry
from app.pdf.services import PDFExportService
from app.pdf.validation import PDFExportValidator, PDFValidationError
from app.sessions.models import FormSession
from app.sessions.security import hash_ownership_token
from app.sessions.services import (
    StateConflictError,
    UnauthorizedError,
    ValidationError,
)


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
    form.textfield(name="last_name", x=100, y=200, width=100, height=20)
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
                "maxLength": 10,
                "overflow": "reject",
            },
            {
                "fieldKey": "last_name",
                "pdfFieldName": "last_name",
                "format": "person_name",
                "maxLength": 10,
                "overflow": "truncate",
            },
        ],
    }
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(mapping_data, f)
    return mapping_path


# --- 1. Mapping Validation Tests ---


def test_mapping_loader_valid(
    test_fixtures_dir: Path, mock_pdf_template: Path, mock_pdf_mapping: Path
) -> None:
    registry = PDFTemplateRegistry(test_fixtures_dir)
    loader = PDFMappingLoader(registry)
    mapping = loader.load_mapping("basic-registration-v1")
    assert mapping.template_key == "basic-registration-v1"
    assert len(mapping.fields) == 2


def test_mapping_loader_missing_files(test_fixtures_dir: Path) -> None:
    registry = PDFTemplateRegistry(test_fixtures_dir)
    loader = PDFMappingLoader(registry)
    with pytest.raises(PDFMappingError, match="not found"):
        loader.load_mapping("non-existent")


def test_mapping_loader_duplicate_keys(test_fixtures_dir: Path, tmp_path: Path) -> None:
    mapping_path = test_fixtures_dir / "duplicate.mapping.json"
    mapping_data = {
        "templateKey": "duplicate",
        "formVersionKey": "basic-registration:1",
        "mappingVersion": 1,
        "strategy": "acroform",
        "fields": [
            {"fieldKey": "name", "pdfFieldName": "field1", "format": "text"},
            {"fieldKey": "name", "pdfFieldName": "field2", "format": "text"},
        ],
    }
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(mapping_data, f)

    registry = PDFTemplateRegistry(test_fixtures_dir)
    loader = PDFMappingLoader(registry)
    with pytest.raises(PDFMappingError, match="Duplicate mapping field key"):
        loader.load_mapping("duplicate")


# --- 2. Formatting Tests ---


def test_formatting_dates() -> None:
    assert (
        format_field_value(
            field_type="date",
            normalized_value="1995-04-12",
            output_value=None,
            output_language="de",
        )
        == "12.04.1995"
    )

    assert (
        format_field_value(
            field_type="date",
            normalized_value="1995-04-12",
            output_value=None,
            output_language="fr",
        )
        == "12/04/1995"
    )


def test_formatting_booleans() -> None:
    assert (
        format_field_value(
            field_type="boolean",
            normalized_value=True,
            output_value=None,
            output_language="en",
        )
        == "Yes"
    )

    assert (
        format_field_value(
            field_type="boolean",
            normalized_value=False,
            output_value=None,
            output_language="de",
        )
        == "Nein"
    )


def test_formatting_multiple_choices() -> None:
    assert (
        format_field_value(
            field_type="multiple_choice",
            normalized_value=["apple", "banana"],
            output_value=None,
            output_language="en",
        )
        == "Apple, Banana"
    )


# --- 3. Overflow & Validation Tests ---


def test_pdf_validator_valid(tmp_path: Path) -> None:
    path = tmp_path / "valid.pdf"
    with open(path, "wb") as f:
        f.write(b"%PDF-1.4\nhello")
    validator = PDFExportValidator()
    checksum = validator.validate(path)
    assert len(checksum) == 64  # valid SHA-256


def test_pdf_validator_invalid_signature(tmp_path: Path) -> None:
    path = tmp_path / "invalid.pdf"
    with open(path, "wb") as f:
        f.write(b"NOTAPDF signature hello")
    validator = PDFExportValidator()
    with pytest.raises(PDFValidationError, match="valid PDF header"):
        validator.validate(path)


# --- 4. Export Eligibility & Service Integration ---


def test_export_service_eligibility(
    test_fixtures_dir: Path, mock_pdf_template: Path, mock_pdf_mapping: Path
) -> None:
    db = SessionLocal()
    try:
        # Create Template
        template = FormTemplate(key="basic-registration", name="Basic Registration")
        db.add(template)
        db.commit()

        # Create Version
        version = FormVersion(
            form_template_id=template.id,
            version_number=1,
            status="published",
            source_language="en",
            supported_output_languages=["en", "de"],
        )
        db.add(version)
        db.commit()

        # Create Fields
        field1 = FormField(
            form_version_id=version.id,
            key="first_name",
            field_type="person_name",
            required=True,
            position=1,
        )
        field2 = FormField(
            form_version_id=version.id,
            key="last_name",
            field_type="person_name",
            required=True,
            position=2,
        )
        db.add_all([field1, field2])
        db.commit()

        # Create Session in completed state
        token = "test-token"
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
        db.add(session)
        db.commit()

        # Create answers
        ans1 = FormAnswer(
            session_id=session.id,
            field_id=field1.id,
            original_answer="Lina",
            original_language="en",
            normalized_value="Lina",
            output_value="Lina",
            status="confirmed",
            confirmed_by_user=True,
        )
        ans2 = FormAnswer(
            session_id=session.id,
            field_id=field2.id,
            original_answer="Example",
            original_language="en",
            normalized_value="Example",
            output_value="Example",
            status="confirmed",
            confirmed_by_user=True,
        )
        db.add_all([ans1, ans2])
        db.commit()

        service = PDFExportService(db, test_fixtures_dir)

        # 1. Successful Export creation (Idempotent 1st request)
        export = service.create_export(session.public_id, token)
        assert export.status == "completed"
        assert export.file_size is not None
        assert export.file_size > 0
        assert Path(export.storage_path).exists()

        # 2. Idempotent repeated request (should return the exact same export record)
        export2 = service.create_export(session.public_id, token)
        assert export2.id == export.id

        # 3. Ownership token verification rejection
        with pytest.raises(UnauthorizedError):
            service.create_export(session.public_id, "wrong-token")

        # 4. Expiration check rejection
        session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        db.commit()
        with pytest.raises(StateConflictError, match="expired"):
            service.create_export(session.public_id, token)
    finally:
        db.close()


def test_export_service_overflow_policies(
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
            supported_output_languages=["en", "de"],
        )
        db.add(version)
        db.commit()

        field1 = FormField(
            form_version_id=version.id,
            key="first_name",
            field_type="person_name",
            required=True,
            position=1,
        )
        field2 = FormField(
            form_version_id=version.id,
            key="last_name",
            field_type="person_name",
            required=True,
            position=2,
        )
        db.add_all([field1, field2])
        db.commit()

        token = "test-token"
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
        db.add(session)
        db.commit()

        # ans1 first_name mapping has maxLength=10 and overflow="reject"
        ans1 = FormAnswer(
            session_id=session.id,
            field_id=field1.id,
            original_answer="ThisNameIsLongerThan10Chars",
            original_language="en",
            normalized_value="ThisNameIsLongerThan10Chars",
            output_value="ThisNameIsLongerThan10Chars",
            status="confirmed",
            confirmed_by_user=True,
        )
        # ans2 last_name mapping has maxLength=10 and overflow="truncate"
        ans2 = FormAnswer(
            session_id=session.id,
            field_id=field2.id,
            original_answer="ExampleSurname",
            original_language="en",
            normalized_value="ExampleSurname",
            output_value="ExampleSurname",
            status="confirmed",
            confirmed_by_user=True,
        )
        db.add_all([ans1, ans2])
        db.commit()

        service = PDFExportService(db, test_fixtures_dir)

        # 1. Overflow reject policy triggers validation error
        with pytest.raises(ValidationError, match="do not fit the PDF template"):
            service.create_export(session.public_id, token)

        # 2. Fix ans1 length, verify ans2 is truncated
        ans1.normalized_value = "Lina"  # type: ignore[assignment]
        ans1.output_value = "Lina"
        db.commit()

        export = service.create_export(session.public_id, token)
        assert export.status == "completed"
        assert Path(export.storage_path).exists()
    finally:
        db.close()
