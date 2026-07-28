from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import text

from app.core.config import settings
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
def use_manual_review_mode() -> Generator[None, None, None]:
    """This file tests the Phase 11 manual-confirmation contract of
    create_session_from_confirmed_fields(include_auto_usable=False, the
    default) — see test_orchestration.py for the Phase 13
    include_auto_usable=True behavior."""
    original = settings.FIELD_DETECTION_REVIEW_MODE
    settings.FIELD_DETECTION_REVIEW_MODE = "manual"
    yield
    settings.FIELD_DETECTION_REVIEW_MODE = original


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


@pytest.mark.asyncio
async def test_create_session_requires_at_least_one_confirmed_field(
    tmp_path: Path,
) -> None:
    db, doc, token = _upload_digital_document(tmp_path)
    try:
        service = FieldDetectionService(db, provider=MockFieldDetectionProvider())
        service.request_detection(doc.public_id, token)

        with pytest.raises(FieldDetectionValidationError) as exc_info:
            await service.create_session_from_confirmed_fields(
                doc.public_id, token, "en", "en"
            )
        assert exc_info.value.error_code == "field_detection_invalid_result"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_create_session_from_confirmed_fields_starts_guided_session(
    tmp_path: Path,
) -> None:
    db, doc, token = _upload_digital_document(tmp_path)
    try:
        service = FieldDetectionService(db, provider=MockFieldDetectionProvider())
        result = service.request_detection(doc.public_id, token)
        field_id = result.fields[0].public_id

        service.update_field(doc.public_id, token, field_id, review_status="confirmed")

        session, session_token = await service.create_session_from_confirmed_fields(
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


@pytest.mark.asyncio
async def test_create_session_ignores_pending_and_rejected_fields(
    tmp_path: Path,
) -> None:
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

        session, _token = await service.create_session_from_confirmed_fields(
            doc.public_id, token, "en", "en"
        )

        stored_session = SessionRepository(db).get_session_by_public_id(
            session.public_id
        )
        assert len(stored_session.version.fields) == 1
        assert stored_session.version.fields[0].key == "first_field"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_create_session_raises_when_no_detection_result_exists(
    tmp_path: Path,
) -> None:
    db, doc, token = _upload_digital_document(tmp_path)
    try:
        service = FieldDetectionService(db, provider=MockFieldDetectionProvider())
        with pytest.raises(FieldDetectionNotFoundError):
            await service.create_session_from_confirmed_fields(
                doc.public_id, token, "en", "en"
            )
    finally:
        db.close()


@pytest.mark.asyncio
async def test_confirmed_field_labels_types_and_order_are_preserved(
    tmp_path: Path,
) -> None:
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

        session, _token = await service.create_session_from_confirmed_fields(
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


@pytest.mark.asyncio
async def test_radio_candidate_options_are_preserved(tmp_path: Path) -> None:
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

        session, _token = await service.create_session_from_confirmed_fields(
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


@pytest.mark.asyncio
async def test_multiple_choice_candidate_options_are_preserved(tmp_path: Path) -> None:
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

        session, _token = await service.create_session_from_confirmed_fields(
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


@pytest.mark.asyncio
async def test_checkbox_candidate_becomes_boolean_question(tmp_path: Path) -> None:
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

        session, _token = await service.create_session_from_confirmed_fields(
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


@pytest.mark.asyncio
async def test_dynamic_form_version_has_dynamic_origin_and_no_pdf_template(
    tmp_path: Path,
) -> None:
    db, doc, token = _upload_digital_document(tmp_path)
    try:
        service = FieldDetectionService(db, provider=MockFieldDetectionProvider())
        result = service.request_detection(doc.public_id, token)
        service.update_field(
            doc.public_id, token, result.fields[0].public_id, review_status="confirmed"
        )

        session, _token = await service.create_session_from_confirmed_fields(
            doc.public_id, token, "en", "en"
        )

        stored_session = SessionRepository(db).get_session_by_public_id(
            session.public_id
        )
        assert stored_session.version.origin == "dynamic_detection"
        assert stored_session.version.pdf_template_key is None
    finally:
        db.close()


class _FakeTranslatingProvider:
    """A deterministic stand-in for the real AI provider: prefixes
    translated text with the target language so tests can assert exactly
    which language a call was made for, without depending on Ollama."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    async def translate_output(self, request: Any) -> Any:
        from app.ai.schemas import TranslationResult

        self.calls.append(
            (request.text, request.source_language, request.target_language)
        )
        return TranslationResult(
            translatedText=f"[{request.target_language}] {request.text}"
        )


class _FailingTranslationProvider:
    """Simulates an AI outage during label/option translation."""

    async def translate_output(self, request: Any) -> Any:
        from app.ai.errors import AIProviderUnavailableError

        raise AIProviderUnavailableError("Ollama is unreachable")


@pytest.mark.asyncio
async def test_dynamic_field_label_translated_to_german(tmp_path: Path) -> None:
    """English question label translated into German: the source label
    must be preserved (audit) and the German translation actually produced
    via the AI provider, not the raw English text mislabeled as German."""
    candidate = _candidate("full-name", "What is your full name?", "text")
    db, doc, token = _upload_digital_document(tmp_path)
    try:
        provider = _FakeTranslatingProvider()
        service = FieldDetectionService(
            db,
            provider=MockFieldDetectionProvider(candidates=[candidate]),
            ai_provider=provider,
        )
        result = service.request_detection(doc.public_id, token)
        service.update_field(
            doc.public_id, token, result.fields[0].public_id, review_status="confirmed"
        )

        session, _token = await service.create_session_from_confirmed_fields(
            doc.public_id, token, "de", "de"
        )

        stored_session = SessionRepository(db).get_session_by_public_id(
            session.public_id
        )
        field = stored_session.version.fields[0]
        translations = {t.language: t.label for t in field.translations}

        assert translations["en"] == "What is your full name?"
        assert translations["de"] == "[de] What is your full name?"
        assert provider.calls == [("What is your full name?", "en", "de")]
        assert stored_session.version.source_language == "en"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_dynamic_field_label_translated_to_arabic(tmp_path: Path) -> None:
    candidate = _candidate("full-name", "What is your full name?", "text")
    db, doc, token = _upload_digital_document(tmp_path)
    try:
        provider = _FakeTranslatingProvider()
        service = FieldDetectionService(
            db,
            provider=MockFieldDetectionProvider(candidates=[candidate]),
            ai_provider=provider,
        )
        result = service.request_detection(doc.public_id, token)
        service.update_field(
            doc.public_id, token, result.fields[0].public_id, review_status="confirmed"
        )

        session, _token = await service.create_session_from_confirmed_fields(
            doc.public_id, token, "ar", "ar"
        )

        stored_session = SessionRepository(db).get_session_by_public_id(
            session.public_id
        )
        field = stored_session.version.fields[0]
        translations = {t.language: t.label for t in field.translations}

        assert translations["en"] == "What is your full name?"
        assert translations["ar"] == "[ar] What is your full name?"
        assert provider.calls == [("What is your full name?", "en", "ar")]
    finally:
        db.close()


@pytest.mark.asyncio
async def test_dynamic_choice_labels_translated_preserve_stable_values(
    tmp_path: Path,
) -> None:
    """Translated choice labels preserve stable option values: the value
    used by answer validation must never change, only the display label."""
    from app.field_detection.providers.base import DetectedFieldCandidate

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
    db, doc, token = _upload_digital_document(tmp_path)
    try:
        provider = _FakeTranslatingProvider()
        service = FieldDetectionService(
            db,
            provider=MockFieldDetectionProvider(candidates=[candidate]),
            ai_provider=provider,
        )
        result = service.request_detection(doc.public_id, token)
        service.update_field(
            doc.public_id, token, result.fields[0].public_id, review_status="confirmed"
        )

        session, _token = await service.create_session_from_confirmed_fields(
            doc.public_id, token, "de", "de"
        )

        stored_session = SessionRepository(db).get_session_by_public_id(
            session.public_id
        )
        field = stored_session.version.fields[0]

        # Stable values are the original English option strings, in order,
        # regardless of the display language.
        assert [o.value for o in field.options] == ["Housing", "Education", "Medical"]

        for option in field.options:
            by_lang = {t.language: t.label for t in option.translations}
            assert by_lang["en"] == option.value  # original source label kept
            assert by_lang["de"] == f"[de] {option.value}"  # translated display label
    finally:
        db.close()


@pytest.mark.asyncio
async def test_dynamic_field_no_translation_call_when_languages_match(
    tmp_path: Path,
) -> None:
    """Output-language translation is performed only when needed: no AI
    call at all when user_language already matches the assumed source
    language."""
    candidate = _candidate("full-name", "Full Name", "text")
    db, doc, token = _upload_digital_document(tmp_path)
    try:
        provider = _FakeTranslatingProvider()
        service = FieldDetectionService(
            db,
            provider=MockFieldDetectionProvider(candidates=[candidate]),
            ai_provider=provider,
        )
        result = service.request_detection(doc.public_id, token)
        service.update_field(
            doc.public_id, token, result.fields[0].public_id, review_status="confirmed"
        )

        session, _token = await service.create_session_from_confirmed_fields(
            doc.public_id, token, "en", "en"
        )

        stored_session = SessionRepository(db).get_session_by_public_id(
            session.public_id
        )
        field = stored_session.version.fields[0]

        assert provider.calls == []
        assert [t.language for t in field.translations] == ["en"]
    finally:
        db.close()


@pytest.mark.asyncio
async def test_dynamic_field_translation_failure_falls_back_to_source_text(
    tmp_path: Path,
) -> None:
    """AI failures preserve the original text and produce a safe fallback:
    if translation fails, the user_language label falls back to the
    original source text rather than blocking question creation."""
    candidate = _candidate("full-name", "Full Name", "text")
    db, doc, token = _upload_digital_document(tmp_path)
    try:
        service = FieldDetectionService(
            db,
            provider=MockFieldDetectionProvider(candidates=[candidate]),
            ai_provider=_FailingTranslationProvider(),
        )
        result = service.request_detection(doc.public_id, token)
        service.update_field(
            doc.public_id, token, result.fields[0].public_id, review_status="confirmed"
        )

        session, _token = await service.create_session_from_confirmed_fields(
            doc.public_id, token, "de", "de"
        )

        stored_session = SessionRepository(db).get_session_by_public_id(
            session.public_id
        )
        field = stored_session.version.fields[0]
        translations = {t.language: t.label for t in field.translations}

        assert translations["en"] == "Full Name"
        assert translations["de"] == "Full Name"  # safe fallback, not blocked
    finally:
        db.close()


@pytest.mark.asyncio
async def test_dynamic_field_user_language_and_output_language_independent(
    tmp_path: Path,
) -> None:
    """user_language and output_language remain independent: a session can
    request German questions with English output_language, and the created
    FormSession must record each distinctly."""
    candidate = _candidate("full-name", "Full Name", "text")
    db, doc, token = _upload_digital_document(tmp_path)
    try:
        provider = _FakeTranslatingProvider()
        service = FieldDetectionService(
            db,
            provider=MockFieldDetectionProvider(candidates=[candidate]),
            ai_provider=provider,
        )
        result = service.request_detection(doc.public_id, token)
        service.update_field(
            doc.public_id, token, result.fields[0].public_id, review_status="confirmed"
        )

        session, _token = await service.create_session_from_confirmed_fields(
            doc.public_id, token, "de", "en"
        )

        assert session.user_language == "de"
        assert session.output_language == "en"
        assert session.user_language != session.output_language
        # Only the user-facing question language triggered a translation call.
        assert provider.calls == [("Full Name", "en", "de")]
    finally:
        db.close()


@pytest.mark.asyncio
async def test_dynamic_field_translations_not_reused_across_languages(
    tmp_path: Path,
) -> None:
    """Questions created for English must not be reused as German
    questions: two sessions created from the same confirmed detection
    result, for different user_language values, must each get their own
    correctly labeled FormVersion — never sharing translations."""
    candidate = _candidate("full-name", "Full Name", "text")
    db, doc, token = _upload_digital_document(tmp_path)
    try:
        provider = _FakeTranslatingProvider()
        service = FieldDetectionService(
            db,
            provider=MockFieldDetectionProvider(candidates=[candidate]),
            ai_provider=provider,
        )
        result = service.request_detection(doc.public_id, token)
        service.update_field(
            doc.public_id, token, result.fields[0].public_id, review_status="confirmed"
        )

        session_en, _ = await service.create_session_from_confirmed_fields(
            doc.public_id, token, "en", "en"
        )
        session_de, _ = await service.create_session_from_confirmed_fields(
            doc.public_id, token, "de", "de"
        )

        en_field = (
            SessionRepository(db)
            .get_session_by_public_id(session_en.public_id)
            .version.fields[0]
        )
        de_field = (
            SessionRepository(db)
            .get_session_by_public_id(session_de.public_id)
            .version.fields[0]
        )

        en_labels = {t.language: t.label for t in en_field.translations}
        de_labels = {t.language: t.label for t in de_field.translations}

        assert en_labels == {"en": "Full Name"}
        assert de_labels == {"en": "Full Name", "de": "[de] Full Name"}
        # The English-only version must never have acquired a German label.
        assert "de" not in en_labels
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
