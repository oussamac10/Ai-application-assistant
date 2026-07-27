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


def test_confirmed_field_labels_types_and_order_are_preserved(tmp_path: Path) -> None:
    """Guards the "generated guided questions did not correctly correspond to
    the confirmed detected fields" regression: label, field_type, and
    display order must all flow through unchanged from confirmed candidates
    into the generated FormField rows."""
    db, doc, token = _upload_digital_document(tmp_path)
    try:
        candidates = [
            _candidate("c1", "Full Name", "text"),
            _candidate("c2", "Email Address", "email"),
            _candidate("c3", "Phone Number", "phone"),
        ]
        service = FieldDetectionService(
            db, provider=MockFieldDetectionProvider(candidates=candidates)
        )
        result = service.request_detection(doc.public_id, token)

        for field in result.fields:
            service.update_field(
                doc.public_id, token, field.public_id, review_status="confirmed"
            )

        session, _token = service.create_session_from_confirmed_fields(
            doc.public_id, token, "en", "en"
        )

        stored_session = SessionRepository(db).get_session_by_public_id(
            session.public_id
        )
        fields = stored_session.version.fields  # already ordered by position

        assert [f.key for f in fields] == ["full_name", "email_address", "phone_number"]
        assert [f.field_type for f in fields] == ["string", "email", "phone"]
        assert [
            t.label for f in fields for t in f.translations if t.language == "en"
        ] == [
            "Full Name",
            "Email Address",
            "Phone Number",
        ]
        assert [f.position for f in fields] == [0, 1, 2]
    finally:
        db.close()


def test_radio_candidate_options_are_preserved(tmp_path: Path) -> None:
    from app.field_detection.providers.base import DetectedFieldCandidate

    db, doc, token = _upload_digital_document(tmp_path)
    try:
        candidate = DetectedFieldCandidate(
            candidate_key="radio-1",
            page_number=1,
            label="Marital Status",
            normalized_name="marital_status",
            field_type="radio",
            confidence=0.9,
            source="acroform",
            options=("single", "married", "divorced"),
        )
        service = FieldDetectionService(
            db, provider=MockFieldDetectionProvider(candidates=[candidate])
        )
        result = service.request_detection(doc.public_id, token)
        service.update_field(
            doc.public_id, token, result.fields[0].public_id, review_status="confirmed"
        )

        session, _token = service.create_session_from_confirmed_fields(
            doc.public_id, token, "en", "en"
        )

        stored_session = SessionRepository(db).get_session_by_public_id(
            session.public_id
        )
        field = stored_session.version.fields[0]
        assert field.field_type == "single_choice"
        assert [o.value for o in field.options] == ["single", "married", "divorced"]
        for option in field.options:
            assert any(t.language == "en" for t in option.translations)
    finally:
        db.close()


def test_multiple_choice_candidate_options_are_preserved(tmp_path: Path) -> None:
    """Guards the "fieldConfig is empty so we don't know what the options
    are" regression: a confirmed multiple_choice candidate's options must
    flow through, in order, into the generated FormField's real options."""
    from app.field_detection.providers.base import DetectedFieldCandidate

    db, doc, token = _upload_digital_document(tmp_path)
    try:
        candidate = DetectedFieldCandidate(
            candidate_key="choice-1",
            page_number=1,
            label="Request category",
            normalized_name="request_category",
            field_type="multiple_choice",
            confidence=0.85,
            source="native",
            multiple=True,
            options=("Housing", "Education", "Medical"),
        )
        service = FieldDetectionService(
            db, provider=MockFieldDetectionProvider(candidates=[candidate])
        )
        result = service.request_detection(doc.public_id, token)
        service.update_field(
            doc.public_id, token, result.fields[0].public_id, review_status="confirmed"
        )

        session, _token = service.create_session_from_confirmed_fields(
            doc.public_id, token, "en", "en"
        )

        stored_session = SessionRepository(db).get_session_by_public_id(
            session.public_id
        )
        field = stored_session.version.fields[0]
        assert field.field_type == "multiple_choice"
        assert [o.value for o in field.options] == ["Housing", "Education", "Medical"]
        for option in field.options:
            assert any(t.language == "en" for t in option.translations)
    finally:
        db.close()


def test_checkbox_candidate_becomes_boolean_question(tmp_path: Path) -> None:
    candidate = _candidate("cb-1", "I Agree To The Terms", "checkbox")
    db, doc, token = _upload_digital_document(tmp_path)
    try:
        service = FieldDetectionService(
            db, provider=MockFieldDetectionProvider(candidates=[candidate])
        )
        result = service.request_detection(doc.public_id, token)
        service.update_field(
            doc.public_id, token, result.fields[0].public_id, review_status="confirmed"
        )

        session, _token = service.create_session_from_confirmed_fields(
            doc.public_id, token, "en", "en"
        )

        stored_session = SessionRepository(db).get_session_by_public_id(
            session.public_id
        )
        field = stored_session.version.fields[0]
        assert field.field_type == "boolean"
        assert field.options == []
    finally:
        db.close()


def test_dynamic_form_version_has_dynamic_origin_and_no_pdf_template(
    tmp_path: Path,
) -> None:
    db, doc, token = _upload_digital_document(tmp_path)
    try:
        service = FieldDetectionService(db, provider=MockFieldDetectionProvider())
        result = service.request_detection(doc.public_id, token)
        service.update_field(
            doc.public_id, token, result.fields[0].public_id, review_status="confirmed"
        )

        session, _token = service.create_session_from_confirmed_fields(
            doc.public_id, token, "en", "en"
        )

        stored_session = SessionRepository(db).get_session_by_public_id(
            session.public_id
        )
        assert stored_session.version.origin == "dynamic_detection"
        assert stored_session.version.pdf_template_key is None
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
