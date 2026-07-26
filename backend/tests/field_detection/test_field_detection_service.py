from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import text

from app.core.config import settings
from app.database.session import SessionLocal
from app.documents.service import SourceDocumentService
from app.field_detection.errors import (
    FieldDetectionAlreadyProcessingError,
    FieldDetectionNotFoundError,
    FieldDetectionValidationError,
)
from app.field_detection.models import FieldDetectionResult
from app.field_detection.providers.local import LocalFieldDetectionProvider
from app.field_detection.providers.mock import MockFieldDetectionProvider
from app.field_detection.service import FieldDetectionService
from app.ocr.models import OCRResult


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE source_documents CASCADE"))
        db.commit()
        yield
    except Exception:
        db.rollback()
    finally:
        db.close()


def _create_digital_pdf(filepath: str) -> None:
    c = canvas.Canvas(filepath, pagesize=letter)
    c.drawString(100, 700, "Email:")
    c.drawString(200, 700, "john@example.com")
    c.showPage()
    c.save()


def _create_acroform_template_pdf(filepath: str) -> None:
    c = canvas.Canvas(filepath, pagesize=letter)
    c.drawString(
        100,
        750,
        "AI Form Assistant Basic Registration Version 1.0 (Phase 8 Predefined)",
    )
    form = c.acroForm
    for idx, field_name in enumerate(
        [
            "first_name",
            "last_name",
            "date_of_birth",
            "email",
            "country",
            "marital_status",
        ]
    ):
        form.textfield(
            name=field_name,
            tooltip=field_name,
            x=200,
            y=600 - (idx * 50),
            width=200,
            height=20,
            value="",
        )
    c.showPage()
    c.save()


def _create_scanned_pdf(filepath: str, tmp_path: Path) -> None:
    jpeg_path = tmp_path / "temp_image.jpg"
    img = Image.new("RGB", (100, 100), color="blue")
    img.save(jpeg_path, "JPEG")

    c = canvas.Canvas(filepath, pagesize=letter)
    c.drawImage(str(jpeg_path), 0, 0, width=612, height=792)
    c.showPage()
    c.save()


def _upload_document(tmp_path: Path, filename: str, builder) -> tuple:
    pdf_path = tmp_path / filename
    builder(str(pdf_path))

    db = SessionLocal()
    doc_service = SourceDocumentService(db)
    with open(pdf_path, "rb") as f:
        content = f.read()
    doc, token = doc_service.upload_and_analyze(
        filename=filename,
        content_type="application/pdf",
        file_chunks=[content],
        privacy_accepted=True,
        user_language="en",
        output_language="en",
    )
    return db, doc, token


def test_request_detection_succeeds_for_unmatched_digital_document(
    tmp_path: Path,
) -> None:
    db, doc, token = _upload_document(tmp_path, "digital.pdf", _create_digital_pdf)
    try:
        assert doc.analysis_result["next_step"] == "dynamic_field_detection"

        service = FieldDetectionService(db, provider=LocalFieldDetectionProvider())
        result = service.request_detection(doc.public_id, token)

        assert result.status == "completed"
        assert result.source_type == "native"
        assert result.field_count == 1
        assert result.fields[0].label == "Email"
        assert result.fields[0].field_type == "email"
    finally:
        db.close()


def test_request_detection_rejects_supported_template(tmp_path: Path) -> None:
    db, doc, token = _upload_document(
        tmp_path, "template.pdf", _create_acroform_template_pdf
    )
    try:
        assert doc.matched_template_key == "basic-registration-v1"

        service = FieldDetectionService(db, provider=MockFieldDetectionProvider())
        with pytest.raises(FieldDetectionValidationError) as exc_info:
            service.request_detection(doc.public_id, token)
        assert exc_info.value.error_code == "supported_template_detected"
    finally:
        db.close()


def test_request_detection_rejects_missing_ocr(tmp_path: Path) -> None:
    pdf_path = tmp_path / "scanned.pdf"
    _create_scanned_pdf(str(pdf_path), tmp_path)

    db = SessionLocal()
    try:
        doc_service = SourceDocumentService(db)
        with open(pdf_path, "rb") as f:
            content = f.read()
        doc, token = doc_service.upload_and_analyze(
            filename="scanned.pdf",
            content_type="application/pdf",
            file_chunks=[content],
            privacy_accepted=True,
            user_language="en",
            output_language="en",
        )
        assert doc.analysis_result["next_step"] == "ocr_required"

        service = FieldDetectionService(db, provider=MockFieldDetectionProvider())
        with pytest.raises(FieldDetectionValidationError) as exc_info:
            service.request_detection(doc.public_id, token)
        assert exc_info.value.error_code == "ocr_required"
    finally:
        db.close()


def test_request_detection_rejects_incomplete_ocr(tmp_path: Path) -> None:
    pdf_path = tmp_path / "scanned.pdf"
    _create_scanned_pdf(str(pdf_path), tmp_path)

    db = SessionLocal()
    try:
        doc_service = SourceDocumentService(db)
        with open(pdf_path, "rb") as f:
            content = f.read()
        doc, token = doc_service.upload_and_analyze(
            filename="scanned.pdf",
            content_type="application/pdf",
            file_chunks=[content],
            privacy_accepted=True,
            user_language="en",
            output_language="en",
        )

        ocr_result = OCRResult(
            source_document_id=doc.id,
            status="processing",
            language="en",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        db.add(ocr_result)
        db.commit()

        service = FieldDetectionService(db, provider=MockFieldDetectionProvider())
        with pytest.raises(FieldDetectionValidationError) as exc_info:
            service.request_detection(doc.public_id, token)
        assert exc_info.value.error_code == "ocr_not_complete"
    finally:
        db.close()


def test_request_detection_is_idempotent(tmp_path: Path) -> None:
    db, doc, token = _upload_document(tmp_path, "digital.pdf", _create_digital_pdf)
    try:
        service = FieldDetectionService(db, provider=MockFieldDetectionProvider())
        first = service.request_detection(doc.public_id, token)
        second = service.request_detection(doc.public_id, token)

        assert first.id == second.id
        assert second.status == "completed"
    finally:
        db.close()


def test_request_detection_raises_when_already_processing(tmp_path: Path) -> None:
    db, doc, token = _upload_document(tmp_path, "digital.pdf", _create_digital_pdf)
    try:
        service = FieldDetectionService(db, provider=MockFieldDetectionProvider())

        processing = FieldDetectionResult(
            source_document_id=doc.id,
            status="processing",
            analysis_version=settings.FIELD_DETECTION_ANALYSIS_VERSION,
            source_type="native",
            expires_at=doc.expires_at,
        )
        service.repo.create(db, processing)

        with pytest.raises(FieldDetectionAlreadyProcessingError):
            service.request_detection(doc.public_id, token)
    finally:
        db.close()


def test_request_detection_failure_marks_result_failed(tmp_path: Path) -> None:
    db, doc, token = _upload_document(tmp_path, "digital.pdf", _create_digital_pdf)
    try:
        service = FieldDetectionService(
            db, provider=MockFieldDetectionProvider(simulate_failure=True)
        )
        with pytest.raises(FieldDetectionValidationError) as exc_info:
            service.request_detection(doc.public_id, token)
        assert exc_info.value.error_code == "field_detection_failed"

        stored = service.repo.get_by_source_document_and_version(
            db, doc.id, settings.FIELD_DETECTION_ANALYSIS_VERSION
        )
        assert stored is not None
        assert stored.status == "failed"
        assert stored.error_code == "field_detection_failed"
    finally:
        db.close()


def test_get_detection_result_not_found(tmp_path: Path) -> None:
    db, doc, token = _upload_document(tmp_path, "digital.pdf", _create_digital_pdf)
    try:
        service = FieldDetectionService(db, provider=MockFieldDetectionProvider())
        with pytest.raises(FieldDetectionNotFoundError):
            service.get_detection_result(doc.public_id, token)
    finally:
        db.close()
