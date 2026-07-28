"""Tests for the Phase 13 automatic upload-to-questions orchestration
service (`PrepareQuestionsService`): the single entrypoint that composes
analysis -> OCR (if needed) -> field detection -> confidence routing ->
question generation -> session creation/reuse."""

from collections.abc import Generator
from pathlib import Path

import pytest
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import text

import app.main  # noqa: F401  # registers every SQLAlchemy mapper (e.g. User) once
from app.ai.mock_provider import MockAIProvider
from app.database.session import SessionLocal
from app.documents.service import SourceDocumentService
from app.field_detection.orchestration import PrepareQuestionsService
from app.field_detection.providers.base import DetectedFieldCandidate
from app.field_detection.providers.mock import MockFieldDetectionProvider
from app.forms.models import FormTemplate, FormVersion


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
    c.drawString(100, 700, "Just some unmatched content")
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


def _upload(tmp_path: Path, filename: str, builder, *args) -> tuple:
    pdf_path = tmp_path / filename
    builder(str(pdf_path), *args)
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


def _publish_basic_registration_template(db) -> None:
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


@pytest.mark.asyncio
async def test_known_form_bypasses_ocr_and_detection(tmp_path: Path) -> None:
    db, doc, token = _upload(tmp_path, "template.pdf", _create_acroform_template_pdf)
    try:
        _publish_basic_registration_template(db)
        assert doc.analysis_result["next_step"] == "supported_template"

        service = PrepareQuestionsService(db, ai_provider=MockAIProvider())
        result = await service.prepare(doc.public_id, token, "en", "en")

        assert result.status == "ready"
        assert result.session is not None
        assert result.ownership_token is not None
        assert result.uncertainty is None
    finally:
        db.close()


@pytest.mark.asyncio
async def test_unknown_digital_pdf_high_confidence_auto_generates_questions(
    tmp_path: Path,
) -> None:
    db, doc, token = _upload(tmp_path, "digital.pdf", _create_digital_pdf)
    try:
        assert doc.analysis_result["next_step"] == "dynamic_field_detection"

        service = PrepareQuestionsService(
            db,
            ai_provider=MockAIProvider(),
            field_detection_provider=MockFieldDetectionProvider(),
        )
        result = await service.prepare(doc.public_id, token, "en", "en")

        assert result.status == "ready"
        assert result.session is not None
        assert result.ownership_token is not None
        assert result.uncertainty is None
    finally:
        db.close()


@pytest.mark.asyncio
async def test_scanned_pdf_runs_ocr_then_generates_questions(tmp_path: Path) -> None:
    db, doc, token = _upload(tmp_path, "scanned.pdf", _create_scanned_pdf, tmp_path)
    try:
        assert doc.analysis_result["next_step"] == "ocr_required"

        service = PrepareQuestionsService(
            db,
            ai_provider=MockAIProvider(),
            field_detection_provider=MockFieldDetectionProvider(),
        )
        result = await service.prepare(doc.public_id, token, "en", "en")

        assert result.status == "ready"
        assert result.session is not None
    finally:
        db.close()


@pytest.mark.asyncio
async def test_low_confidence_field_surfaces_uncertainty_but_does_not_block(
    tmp_path: Path,
) -> None:
    db, doc, token = _upload(tmp_path, "digital.pdf", _create_digital_pdf)
    try:
        candidates = [
            DetectedFieldCandidate(
                candidate_key="c1",
                page_number=1,
                label="Email",
                normalized_name="email",
                field_type="email",
                confidence=0.9,
                source="native",
            ),
            DetectedFieldCandidate(
                candidate_key="c2",
                page_number=1,
                label="Ambiguous mark",
                normalized_name="ambiguous_mark",
                field_type="unknown",
                confidence=0.2,
                source="native",
            ),
        ]
        provider = MockFieldDetectionProvider(candidates=candidates)
        service = PrepareQuestionsService(
            db, ai_provider=MockAIProvider(), field_detection_provider=provider
        )
        result = await service.prepare(doc.public_id, token, "en", "en")

        assert result.status == "ready"
        assert result.session is not None
        assert result.uncertainty is not None
        assert result.uncertainty.has_uncertain_fields is True
        assert result.uncertainty.uncertain_field_count == 1
    finally:
        db.close()


@pytest.mark.asyncio
async def test_all_fields_low_confidence_returns_needs_clarification_not_failure(
    tmp_path: Path,
) -> None:
    db, doc, token = _upload(tmp_path, "digital.pdf", _create_digital_pdf)
    try:
        candidates = [
            DetectedFieldCandidate(
                candidate_key="c1",
                page_number=1,
                label="Unclear mark",
                normalized_name="unclear_mark",
                field_type="unknown",
                confidence=0.1,
                source="native",
            ),
        ]
        provider = MockFieldDetectionProvider(candidates=candidates)
        service = PrepareQuestionsService(
            db, ai_provider=MockAIProvider(), field_detection_provider=provider
        )
        result = await service.prepare(doc.public_id, token, "en", "en")

        assert result.status == "needs_clarification"
        assert result.session is None
        assert result.error_code == "no_usable_questions"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_repeated_orchestration_call_is_idempotent_no_duplicate_session(
    tmp_path: Path,
) -> None:
    db, doc, token = _upload(tmp_path, "digital.pdf", _create_digital_pdf)
    try:
        service = PrepareQuestionsService(
            db,
            ai_provider=MockAIProvider(),
            field_detection_provider=MockFieldDetectionProvider(),
        )
        first = await service.prepare(doc.public_id, token, "en", "en")
        second = await service.prepare(doc.public_id, token, "en", "en")

        assert first.session is not None
        assert second.session is not None
        assert first.session.public_id == second.session.public_id
        assert second.reused_existing_session is True
        assert second.ownership_token is None
    finally:
        db.close()


@pytest.mark.asyncio
async def test_choice_field_without_options_excluded_from_auto_questions(
    tmp_path: Path,
) -> None:
    db, doc, token = _upload(tmp_path, "digital.pdf", _create_digital_pdf)
    try:
        candidates = [
            DetectedFieldCandidate(
                candidate_key="c1",
                page_number=1,
                label="Email",
                normalized_name="email",
                field_type="email",
                confidence=0.9,
                source="native",
            ),
            DetectedFieldCandidate(
                candidate_key="c2",
                page_number=1,
                label="Preference",
                normalized_name="preference",
                field_type="radio",
                confidence=0.95,
                source="native",
                options=(),
            ),
        ]
        provider = MockFieldDetectionProvider(candidates=candidates)
        service = PrepareQuestionsService(
            db, ai_provider=MockAIProvider(), field_detection_provider=provider
        )
        result = await service.prepare(doc.public_id, token, "en", "en")

        assert result.status == "ready"
        assert result.uncertainty is not None
        assert result.uncertainty.uncertain_field_count == 1
    finally:
        db.close()


@pytest.mark.asyncio
async def test_owner_mismatch_rejected(tmp_path: Path) -> None:
    db, doc, _token = _upload(tmp_path, "digital.pdf", _create_digital_pdf)
    try:
        from app.documents.errors import DocumentUnauthorizedError

        service = PrepareQuestionsService(
            db,
            ai_provider=MockAIProvider(),
            field_detection_provider=MockFieldDetectionProvider(),
        )
        with pytest.raises(DocumentUnauthorizedError):
            await service.prepare(doc.public_id, "wrong-token", "en", "en")
    finally:
        db.close()


@pytest.mark.asyncio
async def test_review_metadata_persisted_without_sensitive_data(tmp_path: Path) -> None:
    db, doc, token = _upload(tmp_path, "digital.pdf", _create_digital_pdf)
    try:
        service = PrepareQuestionsService(
            db,
            ai_provider=MockAIProvider(),
            field_detection_provider=MockFieldDetectionProvider(),
        )
        await service.prepare(doc.public_id, token, "en", "en")

        from app.field_detection.repository import FieldDetectionRepository

        repo = FieldDetectionRepository()
        detection_result = repo.get_by_source_document_and_version(db, doc.id, 1)
        assert detection_result is not None
        assert detection_result.review_metadata is not None
        assert detection_result.review_metadata["autoConfirmedCount"] >= 1
        assert "totalFieldCount" in detection_result.review_metadata
        # No raw label/value text or tokens leak into the persisted metadata.
        serialized = str(detection_result.review_metadata)
        assert token not in serialized
    finally:
        db.close()
