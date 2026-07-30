"""Translation cost of turning a whole document into questions.

Guards the reported failure at the level the user actually experienced it: a
24-field document must not issue one AI call per field, and a retry must not
redo any of the work.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import text as sa_text

import app.main  # noqa: F401  registers every SQLAlchemy mapper once
from app.ai.batch_translation import clear_translation_cache
from app.ai.schemas import BatchTranslationResult, TranslationResult
from app.database.session import SessionLocal
from app.documents.service import SourceDocumentService
from app.field_detection.orchestration import PrepareQuestionsService
from app.field_detection.providers.base import DetectedFieldCandidate
from app.field_detection.providers.mock import MockFieldDetectionProvider
from app.field_detection.service import FieldDetectionService

_FIELD_COUNT = 24


@pytest.fixture(autouse=True)
def clean_state() -> Generator[None, None, None]:
    clear_translation_cache()
    db = SessionLocal()
    try:
        db.execute(sa_text("TRUNCATE TABLE source_documents CASCADE"))
        db.execute(sa_text("TRUNCATE TABLE form_templates CASCADE"))
        db.execute(sa_text("TRUNCATE TABLE form_sessions CASCADE"))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
    yield
    clear_translation_cache()


class _CountingProvider:
    """Counts every AI call the document costs, batched or single."""

    def __init__(self) -> None:
        self.batch_calls = 0
        self.single_calls = 0
        self.texts_seen: list[str] = []

    async def translate_output_batch(self, request: Any) -> BatchTranslationResult:
        self.batch_calls += 1
        self.texts_seen.extend(item.text for item in request.items)
        return BatchTranslationResult(
            translationsById={
                item.id: f"[{request.target_language}] {item.text}"
                for item in request.items
            }
        )

    async def translate_output(self, request: Any) -> TranslationResult:
        self.single_calls += 1
        return TranslationResult(
            translatedText=f"[{request.target_language}] {request.text}"
        )

    @property
    def total_calls(self) -> int:
        return self.batch_calls + self.single_calls


def _candidates() -> list[DetectedFieldCandidate]:
    """24 text fields plus one choice group — the shape of the real rental
    contract, including a repeated label so dedup is exercised."""
    fields = [
        DetectedFieldCandidate(
            candidate_key=f"c{index}",
            page_number=1,
            label="Name" if index in (0, 1) else f"Field {index}",
            normalized_name=f"field_{index}",
            field_type="text",
            confidence=0.9,
            source="native",
        )
        for index in range(_FIELD_COUNT - 1)
    ]
    fields.append(
        DetectedFieldCandidate(
            candidate_key="c_choice",
            page_number=1,
            label="Rooms",
            normalized_name="rooms",
            field_type="multiple_choice",
            confidence=0.9,
            source="native",
            options=("Kitchen", "Bathroom", "Cellar", "Balcony"),
        )
    )
    return fields


def _upload(tmp_path: Path) -> tuple[Any, Any, str]:
    pdf_path = tmp_path / "doc.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    c.setFont("Helvetica", 10)
    c.drawString(40, 700, "Content that matches no template")
    c.showPage()
    c.save()

    db = SessionLocal()
    doc, token = SourceDocumentService(db).upload_and_analyze(
        filename="doc.pdf",
        content_type="application/pdf",
        file_chunks=[pdf_path.read_bytes()],
        privacy_accepted=True,
        user_language="en",
        output_language="de",
    )
    return db, doc, token


@pytest.mark.asyncio
async def test_24_fields_cost_a_bounded_number_of_ai_calls(tmp_path: Path) -> None:
    """Before batching this document cost 28 sequential calls, which is what
    pushed the request past the frontend's ceiling."""
    db, doc, token = _upload(tmp_path)
    try:
        ai = _CountingProvider()
        service = FieldDetectionService(
            db,
            provider=MockFieldDetectionProvider(candidates=_candidates()),
            ai_provider=ai,
        )
        service.request_detection(doc.public_id, token)

        session, _ = await service.create_session_from_confirmed_fields(
            doc.public_id, token, "en", "de", include_auto_usable=True
        )

        assert len(session.version.fields) == _FIELD_COUNT
        # 24 labels + 4 option values, minus one duplicate "Name" = 27 unique
        # texts, at batch_size 12 -> 3 calls.
        assert ai.total_calls <= 4, (
            f"{_FIELD_COUNT} fields cost {ai.total_calls} AI calls; batching "
            "regressed to near one-call-per-field"
        )
        assert ai.single_calls == 0
    finally:
        db.close()


@pytest.mark.asyncio
async def test_duplicate_label_is_sent_to_the_provider_once(tmp_path: Path) -> None:
    db, doc, token = _upload(tmp_path)
    try:
        ai = _CountingProvider()
        service = FieldDetectionService(
            db,
            provider=MockFieldDetectionProvider(candidates=_candidates()),
            ai_provider=ai,
        )
        service.request_detection(doc.public_id, token)
        await service.create_session_from_confirmed_fields(
            doc.public_id, token, "en", "de", include_auto_usable=True
        )

        assert ai.texts_seen.count("Name") == 1
    finally:
        db.close()


@pytest.mark.asyncio
async def test_two_target_languages_reuse_nothing_but_still_batch(
    tmp_path: Path,
) -> None:
    """Two target languages double the calls, not multiply them by the field
    count — and a German translation is never served for French."""
    db, doc, token = _upload(tmp_path)
    try:
        ai = _CountingProvider()
        service = FieldDetectionService(
            db,
            provider=MockFieldDetectionProvider(candidates=_candidates()),
            ai_provider=ai,
        )
        service.request_detection(doc.public_id, token)
        session, _ = await service.create_session_from_confirmed_fields(
            doc.public_id, token, "de", "fr", include_auto_usable=True
        )

        assert ai.total_calls <= 8
        labels = {
            translation.language: translation.label
            for field in session.version.fields
            if field.key == "rooms"
            for translation in field.translations
        }
        assert labels["de"] == "[de] Rooms"
        assert labels["fr"] == "[fr] Rooms"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_retry_reuses_the_session_and_makes_no_ai_calls(tmp_path: Path) -> None:
    """Idempotency, measured: the second prepare must not re-translate, not
    regenerate questions, and not create a second session. This is what makes
    the frontend's retry-on-gateway-failure safe."""
    db, doc, token = _upload(tmp_path)
    try:
        ai = _CountingProvider()
        detection_provider = MockFieldDetectionProvider(candidates=_candidates())

        first = await PrepareQuestionsService(
            db, ai_provider=ai, field_detection_provider=detection_provider
        ).prepare(doc.public_id, token, "en", "de")
        assert first.status == "ready"
        assert first.reused_existing_session is False
        calls_after_first = ai.total_calls
        assert calls_after_first > 0

        second = await PrepareQuestionsService(
            db, ai_provider=ai, field_detection_provider=detection_provider
        ).prepare(doc.public_id, token, "en", "de")

        assert second.status == "ready"
        assert second.reused_existing_session is True
        assert second.session is not None
        assert second.session.public_id == first.session.public_id
        assert ai.total_calls == calls_after_first, (
            "a retry re-translated labels; preparation is not idempotent"
        )
        assert len(second.session.version.fields) == _FIELD_COUNT
    finally:
        db.close()
