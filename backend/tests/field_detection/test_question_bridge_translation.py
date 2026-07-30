"""Language behaviour of question generation, end to end through the bridge.

Phase 15 changed three things a user can observe: the document's source
language is detected rather than assumed, only the interface language is
translated during preparation, and stable choice values stay verbatim.
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
from app.database.session import SessionLocal
from app.documents.service import SourceDocumentService
from app.field_detection.orchestration import PrepareQuestionsService
from app.field_detection.providers.base import DetectedFieldCandidate
from app.field_detection.providers.mock import MockFieldDetectionProvider
from app.field_detection.service import FieldDetectionService
from app.translation.backfill import backfill_language
from app.translation.base import (
    TranslationRequest,
    TranslationResponse,
    TranslationUsage,
)
from app.translation.errors import TranslationProviderError
from app.translation.service import clear_translation_cache

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


class _Translator:
    """Records every call, and reports a configurable detected language."""

    provider_name = "test-translator"

    def __init__(self, detects: str = "en") -> None:
        self.calls = 0
        self.texts_seen: list[str] = []
        self.languages_requested: list[str] = []
        self._detects = detects

    async def translate_batch(self, request: TranslationRequest) -> TranslationResponse:
        self.calls += 1
        self.languages_requested.append(request.target_language)
        self.texts_seen.extend(item.text for item in request.items)
        return TranslationResponse(
            translations_by_id={
                item.id: f"[{request.target_language}] {item.text}"
                for item in request.items
            },
            usage=TranslationUsage(
                provider_name=self.provider_name,
                target_language=request.target_language,
                request_count=1,
                translated_character_count=sum(len(i.text) for i in request.items),
                status_class="2xx",
                detected_source_languages=(self._detects,) * max(len(request.items), 1),
                source_language_is_detected=True,
            ),
        )

    async def health_check(self) -> bool:
        return True


class _DeadTranslator:
    provider_name = "dead"

    def __init__(self) -> None:
        self.calls = 0

    async def translate_batch(self, request: TranslationRequest) -> TranslationResponse:
        self.calls += 1
        raise TranslationProviderError("down", "translation_failed")

    async def health_check(self) -> bool:
        return False


def _candidates() -> list[DetectedFieldCandidate]:
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


def _service(db: Any, translator: Any, fallback: Any = None) -> FieldDetectionService:
    return FieldDetectionService(
        db,
        provider=MockFieldDetectionProvider(candidates=_candidates()),
        translation_provider=translator,
        fallback_translation_provider=fallback,
    )


async def _prepare(
    db: Any, doc: Any, token: str, translator: Any, user: str, output: str
) -> Any:
    service = _service(db, translator)
    service.request_detection(doc.public_id, token)
    session, _ = await service.create_session_from_confirmed_fields(
        doc.public_id, token, user, output, include_auto_usable=True
    )
    return session


def _labels(session: Any, key: str) -> dict[str, str]:
    field = next(f for f in session.version.fields if f.key == key)
    return {t.language: t.label for t in field.translations}


@pytest.mark.asyncio
async def test_whole_document_costs_one_provider_call(tmp_path: Path) -> None:
    """Before Phase 14 this document cost 28 sequential calls; batching made it
    4; an array-capable provider makes it 1."""
    db, doc, token = _upload(tmp_path)
    try:
        translator = _Translator()
        session = await _prepare(db, doc, token, translator, "de", "de")

        assert len(session.version.fields) == _FIELD_COUNT
        assert translator.calls == 1
    finally:
        db.close()


@pytest.mark.asyncio
async def test_duplicate_label_is_sent_once(tmp_path: Path) -> None:
    db, doc, token = _upload(tmp_path)
    try:
        translator = _Translator()
        await _prepare(db, doc, token, translator, "de", "de")

        assert translator.texts_seen.count("Name") == 1
    finally:
        db.close()


@pytest.mark.asyncio
async def test_only_the_interface_language_is_translated_eagerly(
    tmp_path: Path,
) -> None:
    """The output language is not paid for during preparation. Its rows exist
    (publish_version demands them) but hold source text until needed."""
    db, doc, token = _upload(tmp_path)
    try:
        translator = _Translator(detects="en")
        session = await _prepare(db, doc, token, translator, "de", "fr")

        assert translator.languages_requested == [
            "de"
        ], "the output language must not be translated during preparation"
        labels = _labels(session, "rooms")
        assert labels["de"] == "[de] Rooms", "interface language is translated"
        assert labels["fr"] == "Rooms", "output language stays deferred"
        assert labels["en"] == "Rooms", "source language keeps the original"
        assert set(session.version.supported_output_languages) == {"en", "de", "fr"}
    finally:
        db.close()


@pytest.mark.asyncio
async def test_detected_source_language_is_recorded_on_the_version(
    tmp_path: Path,
) -> None:
    """A German document must not be recorded as English. Before detection,
    every generated version claimed `en` regardless of its actual content."""
    db, doc, token = _upload(tmp_path)
    try:
        translator = _Translator(detects="de")
        session = await _prepare(db, doc, token, translator, "en", "en")

        assert session.version.source_language == "de"
        labels = _labels(session, "rooms")
        assert labels["de"] == "Rooms", "original text under its real language"
        assert labels["en"] == "[en] Rooms", "interface language is translated"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_german_document_with_english_ui_is_actually_translated(
    tmp_path: Path,
) -> None:
    """The case the phase exists for. Under the old assumed-source model the
    interface language matched the assumption, so nothing was translated and
    the user read German labels in an English interface."""
    db, doc, token = _upload(tmp_path)
    try:
        translator = _Translator(detects="de")
        session = await _prepare(db, doc, token, translator, "en", "de")

        assert translator.calls == 1
        assert _labels(session, "rooms")["en"] == "[en] Rooms"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_stable_choice_values_are_never_translated(tmp_path: Path) -> None:
    """Only the display label is translated. The value is what validation and
    export use, so translating it would silently break both."""
    db, doc, token = _upload(tmp_path)
    try:
        session = await _prepare(db, doc, token, _Translator(), "ar", "ar")

        choice = next(f for f in session.version.fields if f.key == "rooms")
        assert {o.value for o in choice.options} == {
            "Kitchen",
            "Bathroom",
            "Cellar",
            "Balcony",
        }
        arabic = {
            t.label
            for option in choice.options
            for t in option.translations
            if t.language == "ar"
        }
        assert arabic == {
            "[ar] Kitchen",
            "[ar] Bathroom",
            "[ar] Cellar",
            "[ar] Balcony",
        }
    finally:
        db.close()


@pytest.mark.asyncio
async def test_arabic_interface_language_publishes_and_keeps_its_text(
    tmp_path: Path,
) -> None:
    """RTL is a frontend concern, but it can only work if the backend actually
    stores Arabic text for the interface language."""
    db, doc, token = _upload(tmp_path)
    try:

        class _ArabicTranslator(_Translator):
            async def translate_batch(
                self, request: TranslationRequest
            ) -> TranslationResponse:
                self.calls += 1
                self.languages_requested.append(request.target_language)
                return TranslationResponse(
                    translations_by_id={
                        item.id: f"الاسم {item.id}" for item in request.items
                    },
                    usage=TranslationUsage(
                        provider_name="arabic",
                        target_language=request.target_language,
                        detected_source_languages=("en",),
                    ),
                )

        session = await _prepare(db, doc, token, _ArabicTranslator(), "ar", "ar")

        assert session.version.status == "published"
        assert session.user_language == "ar"
        arabic_labels = [
            t.label
            for f in session.version.fields
            for t in f.translations
            if t.language == "ar"
        ]
        assert len(arabic_labels) == _FIELD_COUNT
        assert all(label.startswith("الاسم") for label in arabic_labels)
    finally:
        db.close()


@pytest.mark.asyncio
async def test_provider_outage_still_produces_a_usable_session(
    tmp_path: Path,
) -> None:
    """A translation outage must degrade to untranslated labels, never to a
    failed document."""
    db, doc, token = _upload(tmp_path)
    try:
        session = await _prepare(db, doc, token, _DeadTranslator(), "de", "de")

        assert session.version.status == "published"
        assert len(session.version.fields) == _FIELD_COUNT
        assert _labels(session, "rooms")["en"] == "Rooms"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_primary_outage_uses_the_fallback_provider(tmp_path: Path) -> None:
    db, doc, token = _upload(tmp_path)
    try:
        primary = _DeadTranslator()
        fallback = _Translator()
        service = _service(db, primary, fallback)
        service.request_detection(doc.public_id, token)
        session, _ = await service.create_session_from_confirmed_fields(
            doc.public_id, token, "de", "de", include_auto_usable=True
        )

        assert primary.calls == 1
        assert fallback.calls == 1
        assert _labels(session, "rooms")["de"] == "[de] Rooms"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_repeated_prepare_makes_zero_provider_calls(tmp_path: Path) -> None:
    """Idempotency, measured. This is what makes the frontend's retry safe."""
    db, doc, token = _upload(tmp_path)
    try:
        translator = _Translator()
        detection = MockFieldDetectionProvider(candidates=_candidates())

        first = await PrepareQuestionsService(
            db,
            field_detection_provider=detection,
            translation_provider=translator,
        ).prepare(doc.public_id, token, "de", "de")
        assert first.status == "ready"
        assert translator.calls == 1

        second = await PrepareQuestionsService(
            db,
            field_detection_provider=detection,
            translation_provider=translator,
        ).prepare(doc.public_id, token, "de", "de")

        assert second.reused_existing_session is True
        assert second.session.public_id == first.session.public_id
        assert translator.calls == 1, "a retry called the translation provider"
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Deferred output language
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_backfill_replaces_deferred_placeholders(tmp_path: Path) -> None:
    db, doc, token = _upload(tmp_path)
    try:
        translator = _Translator(detects="en")
        session = await _prepare(db, doc, token, translator, "de", "fr")
        assert _labels(session, "rooms")["fr"] == "Rooms"

        backfiller = _Translator()
        await backfill_language(db, session.version, "fr", backfiller)

        db.refresh(session.version)
        assert _labels(session, "rooms")["fr"] == "[fr] Rooms"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_backfill_is_idempotent(tmp_path: Path) -> None:
    """Calling it twice must not re-translate, and must never overwrite a real
    translation with a fresh guess."""
    db, doc, token = _upload(tmp_path)
    try:
        session = await _prepare(db, doc, token, _Translator(), "de", "fr")

        first = _Translator()
        await backfill_language(db, session.version, "fr", first)
        assert first.calls == 1

        second = _Translator()
        await backfill_language(db, session.version, "fr", second)
        assert second.calls == 0, "nothing left to do, so nothing may be called"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_backfill_leaves_the_interface_language_alone(tmp_path: Path) -> None:
    db, doc, token = _upload(tmp_path)
    try:
        session = await _prepare(db, doc, token, _Translator(), "de", "fr")
        before = _labels(session, "rooms")["de"]

        await backfill_language(db, session.version, "fr", _Translator())

        db.refresh(session.version)
        assert _labels(session, "rooms")["de"] == before
    finally:
        db.close()


@pytest.mark.asyncio
async def test_backfill_does_not_change_option_values(tmp_path: Path) -> None:
    db, doc, token = _upload(tmp_path)
    try:
        session = await _prepare(db, doc, token, _Translator(), "de", "fr")

        await backfill_language(db, session.version, "fr", _Translator())

        db.refresh(session.version)
        choice = next(f for f in session.version.fields if f.key == "rooms")
        assert {o.value for o in choice.options} == {
            "Kitchen",
            "Bathroom",
            "Cellar",
            "Balcony",
        }
    finally:
        db.close()


@pytest.mark.asyncio
async def test_backfill_of_the_source_language_is_a_no_op(tmp_path: Path) -> None:
    db, doc, token = _upload(tmp_path)
    try:
        session = await _prepare(db, doc, token, _Translator(detects="en"), "de", "fr")

        translator = _Translator()
        await backfill_language(db, session.version, "en", translator)

        assert translator.calls == 0
    finally:
        db.close()
