from collections.abc import Generator
from pathlib import Path

import pytest
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import text

from app.core.config import settings
from app.database.session import SessionLocal
from app.documents.service import SourceDocumentService
from app.ocr.errors import OCRAlreadyProcessingError, OCRValidationError
from app.ocr.providers.mock import MockOCRProvider
from app.ocr.renderer import PDFPageRenderer
from app.ocr.service import OCRService


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


def _create_scanned_pdf(filepath: str, tmp_path: Path) -> None:
    jpeg_path = tmp_path / "temp_image.jpg"
    img = Image.new("RGB", (100, 100), color="blue")
    img.save(jpeg_path, "JPEG")

    c = canvas.Canvas(filepath, pagesize=letter)
    c.drawImage(str(jpeg_path), 0, 0, width=612, height=792)
    c.showPage()
    c.save()


def _create_digital_pdf(filepath: str) -> None:
    c = canvas.Canvas(filepath, pagesize=letter)
    c.drawString(100, 750, "Digital PDF content")
    c.showPage()
    c.save()


def _upload_scanned_document(tmp_path: Path) -> tuple:
    pdf_path = tmp_path / "scanned.pdf"
    _create_scanned_pdf(str(pdf_path), tmp_path)

    db = SessionLocal()
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
    return db, doc, token


def _upload_digital_document(tmp_path: Path) -> tuple:
    pdf_path = tmp_path / "digital.pdf"
    _create_digital_pdf(str(pdf_path))

    db = SessionLocal()
    doc_service = SourceDocumentService(db)
    with open(pdf_path, "rb") as f:
        content = f.read()
    doc, token = doc_service.upload_and_analyze(
        filename="digital.pdf",
        content_type="application/pdf",
        file_chunks=[content],
        privacy_accepted=True,
        user_language="en",
        output_language="en",
    )
    return db, doc, token


def test_request_ocr_succeeds_for_scanned_document(tmp_path: Path) -> None:
    db, doc, token = _upload_scanned_document(tmp_path)
    try:
        service = OCRService(
            db,
            provider=MockOCRProvider(),
            renderer=PDFPageRenderer(dpi=settings.OCR_RENDER_DPI),
        )
        result = service.request_ocr(doc.public_id, token, language="en")

        assert result.status == "completed"
        assert result.provider_name == "mock"
        assert result.page_count == 1
        assert len(result.pages) == 1
        assert result.pages[0].text
    finally:
        db.close()


def test_request_ocr_rejects_non_scanned_document(tmp_path: Path) -> None:
    db, doc, token = _upload_digital_document(tmp_path)
    try:
        service = OCRService(db, provider=MockOCRProvider(), renderer=PDFPageRenderer())
        with pytest.raises(OCRValidationError) as exc_info:
            service.request_ocr(doc.public_id, token, language="en")
        assert exc_info.value.error_code == "ocr_not_required"
    finally:
        db.close()


def test_request_ocr_rejects_unsupported_language(tmp_path: Path) -> None:
    db, doc, token = _upload_scanned_document(tmp_path)
    try:
        service = OCRService(db, provider=MockOCRProvider(), renderer=PDFPageRenderer())
        with pytest.raises(OCRValidationError) as exc_info:
            service.request_ocr(doc.public_id, token, language="es")
        assert exc_info.value.error_code == "unsupported_language"
    finally:
        db.close()


def test_request_ocr_is_idempotent(tmp_path: Path) -> None:
    db, doc, token = _upload_scanned_document(tmp_path)
    try:
        service = OCRService(
            db,
            provider=MockOCRProvider(),
            renderer=PDFPageRenderer(dpi=settings.OCR_RENDER_DPI),
        )
        first = service.request_ocr(doc.public_id, token, language="en")
        second = service.request_ocr(doc.public_id, token, language="en")

        assert first.id == second.id
        assert second.status == "completed"
    finally:
        db.close()


def test_request_ocr_raises_when_already_processing(tmp_path: Path) -> None:
    db, doc, token = _upload_scanned_document(tmp_path)
    try:
        service = OCRService(db, provider=MockOCRProvider(), renderer=PDFPageRenderer())
        existing = service.repo.get_by_source_document_id(db, doc.id)
        assert existing is None

        from datetime import UTC, datetime, timedelta

        from app.ocr.models import OCRResult

        processing = OCRResult(
            source_document_id=doc.id,
            status="processing",
            language="en",
            expires_at=datetime.now(UTC) + timedelta(hours=1),
        )
        service.repo.create(db, processing)

        with pytest.raises(OCRAlreadyProcessingError):
            service.request_ocr(doc.public_id, token, language="en")
    finally:
        db.close()


def test_request_ocr_failure_marks_result_failed(tmp_path: Path) -> None:
    db, doc, token = _upload_scanned_document(tmp_path)
    try:
        service = OCRService(
            db,
            provider=MockOCRProvider(simulate_failure=True),
            renderer=PDFPageRenderer(dpi=settings.OCR_RENDER_DPI),
        )
        with pytest.raises(OCRValidationError) as exc_info:
            service.request_ocr(doc.public_id, token, language="en")
        assert exc_info.value.error_code == "ocr_failed"

        stored = service.repo.get_by_source_document_id(db, doc.id)
        assert stored is not None
        assert stored.status == "failed"
        assert stored.error_code == "ocr_failed"
    finally:
        db.close()


def test_get_ocr_result_not_found(tmp_path: Path) -> None:
    db, doc, token = _upload_scanned_document(tmp_path)
    try:
        service = OCRService(db, provider=MockOCRProvider(), renderer=PDFPageRenderer())
        from app.ocr.errors import OCRNotFoundError

        with pytest.raises(OCRNotFoundError):
            service.get_ocr_result(doc.public_id, token)
    finally:
        db.close()
