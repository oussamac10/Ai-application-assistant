from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pypdf
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import text

from app.commands.cleanup_expired_exports import cleanup_expired_exports
from app.core.config import settings
from app.database.session import SessionLocal
from app.documents.errors import DocumentValidationError
from app.documents.models import SourceDocument
from app.documents.service import SourceDocumentService
from app.forms.models import FormTemplate, FormVersion
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.execute(text("TRUNCATE TABLE source_documents CASCADE"))
        db.execute(text("TRUNCATE TABLE form_sessions CASCADE"))
        db.commit()
        yield
    except Exception:
        db.rollback()
    finally:
        db.close()


def create_simple_pdf(filepath: str, pages: int = 1, text_content: str = "AI Form Assistant Test Content"):
    """Generates a standard text-based digital PDF."""
    c = canvas.Canvas(filepath, pagesize=letter)
    for _ in range(pages):
        c.drawString(100, 750, text_content)
        c.showPage()
    c.save()


def create_acroform_pdf(filepath: str, fields: list[str], text_content: str = "AcroForm test"):
    """Generates a fillable PDF with AcroForm text fields."""
    c = canvas.Canvas(filepath, pagesize=letter)
    c.drawString(100, 750, text_content)
    form = c.acroForm
    for idx, field_name in enumerate(fields):
        form.textfield(
            name=field_name,
            tooltip=field_name,
            x=100,
            y=600 - (idx * 50),
            width=200,
            height=20,
            value=""
        )
    c.showPage()
    c.save()




def create_scanned_pdf(filepath: str, tmp_path: Path):
    """Generates an image-only PDF simulating a scanned document."""
    jpeg_path = tmp_path / "temp_image.jpg"
    img = Image.new("RGB", (100, 100), color="blue")
    img.save(jpeg_path, "JPEG")

    c = canvas.Canvas(filepath, pagesize=letter)
    c.drawImage(str(jpeg_path), 0, 0, width=612, height=792)
    c.showPage()
    c.save()


def encrypt_pdf(input_path: str, output_path: str, password: str):
    """Encrypts a PDF using pypdf."""
    reader = pypdf.PdfReader(input_path)
    writer = pypdf.PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(user_password=password)
    with open(output_path, "wb") as f:
        writer.write(f)


# --- Service and Analyzer Tests ---

def test_upload_and_analyze_digital_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "digital.pdf"
    create_simple_pdf(str(pdf_path), pages=1)

    db = SessionLocal()
    try:
        service = SourceDocumentService(db)
        with open(pdf_path, "rb") as f:
            content = f.read()

        doc, token = service.upload_and_analyze(
            filename="digital.pdf",
            content_type="application/pdf",
            file_chunks=[content],
            privacy_accepted=True,
            user_language="en",
            output_language="en",
        )

        assert doc.status == "analyzed"
        assert doc.document_type == "digital_pdf"
        assert doc.page_count == 1
        assert doc.has_native_text is True
        assert doc.has_acroform is False
        assert doc.is_probably_scanned is False
        assert Path(doc.storage_path).is_file()
        assert doc.expires_at > datetime.now(UTC)

        # Cleanup file manually after test
        service.storage.delete_file(doc.storage_path)
    finally:
        db.close()


def test_upload_and_analyze_fillable_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "fillable.pdf"
    create_acroform_pdf(str(pdf_path), ["first_name", "last_name"])

    db = SessionLocal()
    try:
        service = SourceDocumentService(db)
        with open(pdf_path, "rb") as f:
            content = f.read()

        doc, token = service.upload_and_analyze(
            filename="fillable.pdf",
            content_type="application/pdf",
            file_chunks=[content],
            privacy_accepted=True,
            user_language="en",
            output_language="en",
        )

        assert doc.status == "analyzed"
        assert doc.document_type == "fillable_pdf"
        assert doc.has_acroform is True
        assert len(doc.analysis_result["acroform_fields"]) == 2

        service.storage.delete_file(doc.storage_path)
    finally:
        db.close()


def test_upload_and_analyze_scanned_pdf(tmp_path: Path) -> None:
    pdf_path = tmp_path / "scanned.pdf"
    create_scanned_pdf(str(pdf_path), tmp_path)

    db = SessionLocal()
    try:
        service = SourceDocumentService(db)
        with open(pdf_path, "rb") as f:
            content = f.read()

        doc, token = service.upload_and_analyze(
            filename="scanned.pdf",
            content_type="application/pdf",
            file_chunks=[content],
            privacy_accepted=True,
            user_language="en",
            output_language="en",
        )

        assert doc.status == "analyzed"
        assert doc.document_type == "scanned_pdf"
        assert doc.has_native_text is False
        assert doc.has_embedded_images is True
        assert doc.is_probably_scanned is True

        service.storage.delete_file(doc.storage_path)
    finally:
        db.close()


def test_upload_requires_privacy_accepted(tmp_path: Path) -> None:
    pdf_path = tmp_path / "digital.pdf"
    create_simple_pdf(str(pdf_path), pages=1)

    db = SessionLocal()
    try:
        service = SourceDocumentService(db)
        with open(pdf_path, "rb") as f:
            content = f.read()

        with pytest.raises(DocumentValidationError) as exc:
            service.upload_and_analyze(
                filename="digital.pdf",
                content_type="application/pdf",
                file_chunks=[content],
                privacy_accepted=False,
                user_language="en",
                output_language="en",
            )
        assert exc.value.error_code == "privacy_not_accepted"
    finally:
        db.close()


def test_upload_invalid_mime_type(tmp_path: Path) -> None:
    txt_path = tmp_path / "plain.txt"
    with open(txt_path, "w") as f:
        f.write("Some plain text content.")

    db = SessionLocal()
    try:
        service = SourceDocumentService(db)
        with open(txt_path, "rb") as f:
            content = f.read()

        with pytest.raises(DocumentValidationError) as exc:
            service.upload_and_analyze(
                filename="plain.txt",
                content_type="text/plain",
                file_chunks=[content],
                privacy_accepted=True,
                user_language="en",
                output_language="en",
            )
        assert exc.value.error_code == "invalid_file_type"
    finally:
        db.close()


def test_upload_encrypted_pdf_rejected(tmp_path: Path) -> None:
    pdf_path = tmp_path / "normal.pdf"
    create_simple_pdf(str(pdf_path), pages=1)
    enc_path = tmp_path / "encrypted.pdf"
    encrypt_pdf(str(pdf_path), str(enc_path), "securepassword")

    db = SessionLocal()
    try:
        service = SourceDocumentService(db)
        with open(enc_path, "rb") as f:
            content = f.read()

        with pytest.raises(DocumentValidationError) as exc:
            service.upload_and_analyze(
                filename="encrypted.pdf",
                content_type="application/pdf",
                file_chunks=[content],
                privacy_accepted=True,
                user_language="en",
                output_language="en",
            )
        assert exc.value.error_code in ("encrypted_pdf", "password_protected_pdf")
    finally:
        db.close()


def test_upload_oversized_pdf_rejected(tmp_path: Path) -> None:
    pdf_path = tmp_path / "normal.pdf"
    create_simple_pdf(str(pdf_path), pages=1)

    db = SessionLocal()
    try:
        service = SourceDocumentService(db)
        with open(pdf_path, "rb") as f:
            content = f.read()

        # Set limit temporarily to 50 bytes
        orig_limit = settings.DOCUMENT_UPLOAD_MAX_BYTES
        settings.DOCUMENT_UPLOAD_MAX_BYTES = 50
        try:
            with pytest.raises(DocumentValidationError) as exc:
                service.upload_and_analyze(
                    filename="normal.pdf",
                    content_type="application/pdf",
                    file_chunks=[content],
                    privacy_accepted=True,
                    user_language="en",
                    output_language="en",
                )
            assert exc.value.error_code == "file_too_large"
        finally:
            settings.DOCUMENT_UPLOAD_MAX_BYTES = orig_limit
    finally:
        db.close()


def test_upload_too_many_pages_rejected(tmp_path: Path) -> None:
    pdf_path = tmp_path / "long.pdf"
    create_simple_pdf(str(pdf_path), pages=3)

    db = SessionLocal()
    try:
        service = SourceDocumentService(db)
        with open(pdf_path, "rb") as f:
            content = f.read()

        # Set page limit to 2
        orig_limit = settings.DOCUMENT_UPLOAD_MAX_PAGES
        settings.DOCUMENT_UPLOAD_MAX_PAGES = 2
        try:
            with pytest.raises(DocumentValidationError) as exc:
                service.upload_and_analyze(
                    filename="long.pdf",
                    content_type="application/pdf",
                    file_chunks=[content],
                    privacy_accepted=True,
                    user_language="en",
                    output_language="en",
                )
            assert exc.value.error_code == "too_many_pages"
        finally:
            settings.DOCUMENT_UPLOAD_MAX_PAGES = orig_limit
    finally:
        db.close()


def test_upload_malformed_pdf_rejected(tmp_path: Path) -> None:
    corrupt_path = tmp_path / "corrupt.pdf"
    with open(corrupt_path, "wb") as f:
        f.write(b"%PDF-1.4\n%Malformed and truncated body here without EOF.")

    db = SessionLocal()
    try:
        service = SourceDocumentService(db)
        with open(corrupt_path, "rb") as f:
            content = f.read()

        with pytest.raises(DocumentValidationError) as exc:
            service.upload_and_analyze(
                filename="corrupt.pdf",
                content_type="application/pdf",
                file_chunks=[content],
                privacy_accepted=True,
                user_language="en",
                output_language="en",
            )
        assert exc.value.error_code == "malformed_pdf"
    finally:
        db.close()


# --- Fingerprint Matching and Template Resolution ---

def test_predefined_template_matching(tmp_path: Path) -> None:
    pdf_path = tmp_path / "template.pdf"
    create_acroform_pdf(
        str(pdf_path),
        ["first_name", "last_name", "date_of_birth", "email", "country", "marital_status"],
        text_content="AI Form Assistant Basic Registration Version 1.0 (Phase 8 Predefined)"
    )

    db = SessionLocal()
    try:
        service = SourceDocumentService(db)
        with open(pdf_path, "rb") as f:
            content = f.read()

        doc, token = service.upload_and_analyze(
            filename="registration.pdf",
            content_type="application/pdf",
            file_chunks=[content],
            privacy_accepted=True,
            user_language="en",
            output_language="en",
        )

        assert doc.status == "analyzed"
        assert doc.matched_template_key == "basic-registration-v1"
        assert doc.matched_form_key == "basic-registration"
        assert doc.matched_form_version == 1
        assert doc.analysis_result["next_step"] == "supported_template"

        service.storage.delete_file(doc.storage_path)
    finally:
        db.close()


# --- Endpoint API Tests ---

def test_api_upload_flow(client: TestClient, tmp_path: Path) -> None:
    pdf_path = tmp_path / "api_test.pdf"
    create_acroform_pdf(
        str(pdf_path),
        ["first_name", "last_name", "date_of_birth", "email", "country", "marital_status"],
        text_content="AI Form Assistant Basic Registration Version 1.0 (Phase 8 Predefined)"
    )

    with open(pdf_path, "rb") as f:
        response = client.post(
            "/api/source-documents",
            data={
                "language": "en",
                "outputLanguage": "en",
                "privacyAccepted": "true",
            },
            files={"file": ("registration.pdf", f, "application/pdf")}
        )

    assert response.status_code == 201
    data = response.json()
    assert "documentId" in data
    assert "ownershipToken" in data
    assert data["status"] == "analyzed"
    assert data["analysis"]["pageCount"] == 1
    assert data["analysis"]["hasAcroForm"] is True
    assert data["analysis"]["matchedTemplate"]["templateKey"] == "basic-registration-v1"
    assert data["analysis"]["nextStep"] == "supported_template"

    doc_id = data["documentId"]
    token = data["ownershipToken"]

    # Retrieve safe metadata with header
    get_resp = client.get(
        f"/api/source-documents/{doc_id}",
        headers={"X-Document-Token": token}
    )
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["documentId"] == doc_id
    assert get_data["status"] == "analyzed"
    assert "ownershipToken" not in get_data  # verify no exposure of credentials

    # Reject retrieval with invalid token
    bad_resp = client.get(
        f"/api/source-documents/{doc_id}",
        headers={"X-Document-Token": "invalid_token"}
    )
    assert bad_resp.status_code == 401


def test_api_session_creation_flow(client: TestClient, tmp_path: Path) -> None:
    # Setup database template version
    db = SessionLocal()
    template = FormTemplate(key="basic-registration", name="Basic Registration")
    db.add(template)
    db.commit()

    version = FormVersion(
        form_template_id=template.id,
        version_number=1,
        status="published",
        source_language="en",
        supported_output_languages=["en", "de", "ar"],
    )
    db.add(version)
    db.commit()
    db.close()

    # Upload predefined PDF
    pdf_path = tmp_path / "api_test.pdf"
    create_acroform_pdf(
        str(pdf_path),
        ["first_name", "last_name", "date_of_birth", "email", "country", "marital_status"],
        text_content="AI Form Assistant Basic Registration Version 1.0 (Phase 8 Predefined)"
    )

    with open(pdf_path, "rb") as f:
        response = client.post(
            "/api/source-documents",
            data={
                "language": "en",
                "outputLanguage": "en",
                "privacyAccepted": "true",
            },
            files={"file": ("registration.pdf", f, "application/pdf")}
        )

    data = response.json()
    doc_id = data["documentId"]
    token = data["ownershipToken"]

    # Create guided session from document
    sess_resp = client.post(
        f"/api/source-documents/{doc_id}/session",
        headers={"X-Document-Token": token},
        json={
            "language": "en",
            "outputLanguage": "de"
        }
    )
    assert sess_resp.status_code == 200
    sess_data = sess_resp.json()
    assert "sessionId" in sess_data
    assert "ownershipToken" in sess_data
    assert sess_data["status"] == "created"


# --- Expiration & Cleanup command tests ---

def test_cleanup_expired_source_documents(tmp_path: Path) -> None:
    db = SessionLocal()
    try:
        # Create a document record that has expired
        pdf_path = tmp_path / "expired.pdf"
        create_simple_pdf(str(pdf_path), pages=1)

        doc = SourceDocument(
            public_id="expired-doc-id",
            ownership_token_hash="fakehash",
            original_filename="expired.pdf",
            sanitized_filename="expired.pdf",
            storage_path=str(pdf_path),
            content_type="application/pdf",
            size_bytes=1000,
            checksum_sha256="fakechecksum",
            status="analyzed",
            expires_at=datetime.now(UTC) - timedelta(hours=1),
            created_at=datetime.now(UTC) - timedelta(hours=2),
            updated_at=datetime.now(UTC) - timedelta(hours=2),
        )
        db.add(doc)
        db.commit()

        # Assert file exists
        assert pdf_path.is_file()

        # Run cleanup CLI logic
        res = cleanup_expired_exports()
        assert res == 0

        # Assert document status updated to deleted
        db.refresh(doc)
        assert doc.status == "deleted"
        # Assert file deleted from disk
        assert not pdf_path.exists()
    finally:
        db.close()
