"""Resilience regression tests for question_bridge.create_session_from_confirmed_fields:
one invalid detected field must not fail the whole document when other
usable fields exist (task: "one bad candidate must not fail the whole
document")."""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import text

import app.main  # noqa: F401  registers every SQLAlchemy mapper once
from app.database.session import SessionLocal
from app.documents.service import SourceDocumentService
from app.field_detection.providers.base import DetectedFieldCandidate
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
    c.drawString(100, 700, "Just some content")
    c.showPage()
    c.save()


def _upload(tmp_path: Path) -> tuple:
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


@pytest.mark.asyncio
async def test_one_invalid_choice_field_skipped_other_fields_still_succeed(
    tmp_path: Path,
) -> None:
    """A multiple_choice candidate with duplicate option values (e.g. the
    local detector accidentally captures the same option label twice) is
    rejected by FormService.add_field_to_draft's own validation. Before
    this fix, that single bad field aborted question generation for the
    *entire* document; now it is skipped and every other usable field still
    becomes a real guided question."""
    db, doc, token = _upload(tmp_path)
    try:
        candidates = [
            DetectedFieldCandidate(
                candidate_key="c1",
                page_number=1,
                label="Full Name",
                normalized_name="full_name",
                field_type="text",
                confidence=0.95,
                source="native",
            ),
            DetectedFieldCandidate(
                candidate_key="c2",
                page_number=1,
                label="Preference",
                normalized_name="preference",
                field_type="multiple_choice",
                confidence=0.9,
                source="native",
                # Duplicate option values — invalid, must be skipped.
                options=("Yes", "Yes", "No"),
            ),
            DetectedFieldCandidate(
                candidate_key="c3",
                page_number=1,
                label="Email",
                normalized_name="email",
                field_type="email",
                confidence=0.9,
                source="native",
            ),
        ]
        provider = MockFieldDetectionProvider(candidates=candidates)
        service = FieldDetectionService(db, provider=provider)
        result = service.request_detection(doc.public_id, token)

        for field in result.fields:
            service.update_field(
                doc.public_id, token, field.public_id, review_status="confirmed"
            )

        session, session_token = await service.create_session_from_confirmed_fields(
            doc.public_id, token, "en", "en"
        )

        assert session_token
        stored = SessionRepository(db).get_session_by_public_id(session.public_id)
        assert stored is not None
        field_keys = {f.key for f in stored.version.fields}
        # The two good fields made it through; the bad one was skipped.
        assert "full_name" in field_keys
        assert "email" in field_keys
        assert "preference" not in field_keys
        assert len(stored.version.fields) == 2
    finally:
        db.close()


@pytest.mark.asyncio
async def test_all_candidates_invalid_still_raises_safely(tmp_path: Path) -> None:
    """If *every* confirmed candidate is invalid, the document must still
    fail safely with the existing, already-handled error_code rather than
    creating an empty/meaningless session."""
    from app.field_detection.errors import FieldDetectionValidationError

    db, doc, token = _upload(tmp_path)
    try:
        candidates = [
            DetectedFieldCandidate(
                candidate_key="c1",
                page_number=1,
                label="Preference",
                normalized_name="preference",
                field_type="multiple_choice",
                confidence=0.9,
                source="native",
                options=("Yes", "Yes"),
            ),
        ]
        provider = MockFieldDetectionProvider(candidates=candidates)
        service = FieldDetectionService(db, provider=provider)
        result = service.request_detection(doc.public_id, token)
        service.update_field(
            doc.public_id, token, result.fields[0].public_id, review_status="confirmed"
        )

        with pytest.raises(FieldDetectionValidationError) as exc_info:
            await service.create_session_from_confirmed_fields(
                doc.public_id, token, "en", "en"
            )
        assert exc_info.value.error_code == "field_detection_invalid_result"
    finally:
        db.close()
