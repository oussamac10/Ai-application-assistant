from collections.abc import Generator
from pathlib import Path

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import text

from app.database.session import SessionLocal
from app.documents.service import SourceDocumentService
from app.field_detection.errors import (
    FieldDetectionNotFoundError,
    FieldDetectionValidationError,
)
from app.field_detection.providers.mock import MockFieldDetectionProvider
from app.field_detection.service import FieldDetectionService
from app.sessions.repositories import SessionRepository


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE source_documents CASCADE"))
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.execute(text("TRUNCATE TABLE form_sessions CASCADE"))
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


def test_create_session_requires_at_least_one_confirmed_field(tmp_path: Path) -> None:
    db, doc, token = _upload_digital_document(tmp_path)
    try:
        service = FieldDetectionService(db, provider=MockFieldDetectionProvider())
        service.request_detection(doc.public_id, token)

        with pytest.raises(FieldDetectionValidationError) as exc_info:
            service.create_session_from_confirmed_fields(
                doc.public_id, token, "en", "en"
            )
        assert exc_info.value.error_code == "field_detection_invalid_result"
    finally:
        db.close()


def test_create_session_from_confirmed_fields_starts_guided_session(
    tmp_path: Path,
) -> None:
    db, doc, token = _upload_digital_document(tmp_path)
    try:
        service = FieldDetectionService(db, provider=MockFieldDetectionProvider())
        result = service.request_detection(doc.public_id, token)
        field_id = result.fields[0].public_id

        service.update_field(doc.public_id, token, field_id, review_status="confirmed")

        session, session_token = service.create_session_from_confirmed_fields(
            doc.public_id, token, "en", "en"
        )

        assert session.status == "session_created"
        assert session_token

        stored_session = SessionRepository(db).get_session_by_public_id(
            session.public_id
        )
        assert stored_session is not None
        assert len(stored_session.version.fields) == 1
        assert stored_session.version.status == "published"
        assert stored_session.version.fields[0].field_type == "string"
    finally:
        db.close()


def test_create_session_ignores_pending_and_rejected_fields(tmp_path: Path) -> None:
    db, doc, token = _upload_digital_document(tmp_path)
    try:
        provider = MockFieldDetectionProvider(
            candidates=[
                _candidate("field-1", "First Field", "text"),
                _candidate("field-2", "Second Field", "text"),
            ]
        )
        service = FieldDetectionService(db, provider=provider)
        result = service.request_detection(doc.public_id, token)

        confirmed_field_id = result.fields[0].public_id
        rejected_field_id = result.fields[1].public_id

        service.update_field(
            doc.public_id, token, confirmed_field_id, review_status="confirmed"
        )
        service.reject_field(doc.public_id, token, rejected_field_id)

        session, _token = service.create_session_from_confirmed_fields(
            doc.public_id, token, "en", "en"
        )

        stored_session = SessionRepository(db).get_session_by_public_id(
            session.public_id
        )
        assert len(stored_session.version.fields) == 1
        assert stored_session.version.fields[0].key == "first_field"
    finally:
        db.close()


def test_create_session_raises_when_no_detection_result_exists(tmp_path: Path) -> None:
    db, doc, token = _upload_digital_document(tmp_path)
    try:
        service = FieldDetectionService(db, provider=MockFieldDetectionProvider())
        with pytest.raises(FieldDetectionNotFoundError):
            service.create_session_from_confirmed_fields(
                doc.public_id, token, "en", "en"
            )
    finally:
        db.close()


def _candidate(key: str, label: str, field_type: str):
    from app.field_detection.providers.base import DetectedFieldCandidate

    return DetectedFieldCandidate(
        candidate_key=key,
        page_number=1,
        label=label,
        normalized_name=label.lower().replace(" ", "_"),
        field_type=field_type,
        confidence=0.9,
        source="native",
    )
