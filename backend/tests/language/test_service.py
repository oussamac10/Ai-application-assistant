"""Persistence, reuse and precedence for the document's source language."""

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
from app.language.detector import (
    UNDETERMINED,
    DetectedLanguage,
    MockDocumentLanguageDetector,
)
from app.language.sampling import build_language_sample, has_enough_text
from app.language.service import DocumentLanguageService, dominant_language

GERMAN = (
    "Mietvertrag für Wohnraum. Der Vermieter und der Mieter schließen den "
    "folgenden Vertrag. Die Miete beträgt monatlich Euro und ist im Voraus zu "
    "zahlen."
)


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    db = SessionLocal()
    try:
        db.execute(sa_text("TRUNCATE TABLE source_documents CASCADE"))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
    yield


def _upload(tmp_path: Path) -> tuple[Any, Any]:
    pdf_path = tmp_path / "doc.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=A4)
    c.drawString(40, 700, "content")
    c.showPage()
    c.save()
    db = SessionLocal()
    doc, _token = SourceDocumentService(db).upload_and_analyze(
        filename="doc.pdf",
        content_type="application/pdf",
        file_chunks=[pdf_path.read_bytes()],
        privacy_accepted=True,
        user_language="en",
        output_language="en",
    )
    return db, doc


# ---------------------------------------------------------------------------
# Detect + persist + reuse
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_detects_and_persists(tmp_path: Path) -> None:
    db, doc = _upload(tmp_path)
    try:
        result = await DocumentLanguageService(db).ensure_detected(doc, GERMAN)
        assert result.language == "de"
        assert doc.detected_source_language == "de"
        assert doc.language_detection_provider == "local"
        assert doc.language_detected_at is not None
    finally:
        db.close()


@pytest.mark.asyncio
async def test_persisted_result_avoids_a_second_detector_call(tmp_path: Path) -> None:
    """A repeat prepare-questions request must cost nothing."""
    db, doc = _upload(tmp_path)
    try:
        detector = MockDocumentLanguageDetector("de")
        service = DocumentLanguageService(db, detector)
        await service.ensure_detected(doc, GERMAN)
        assert detector.calls == 1

        again = await service.ensure_detected(doc, GERMAN)
        assert again.language == "de"
        assert detector.calls == 1, "stored result must be reused"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_stored_und_is_a_result_and_is_reused(tmp_path: Path) -> None:
    db, doc = _upload(tmp_path)
    try:
        detector = MockDocumentLanguageDetector("de")
        service = DocumentLanguageService(db, detector)
        await service.ensure_detected(doc, "Name")  # too short -> und
        assert doc.detected_source_language == UNDETERMINED
        assert detector.calls == 0, "no point asking about text this short"

        await service.ensure_detected(doc, GERMAN)
        assert detector.calls == 0, "a stored und is still a stored result"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_force_reruns_detection(tmp_path: Path) -> None:
    db, doc = _upload(tmp_path)
    try:
        detector = MockDocumentLanguageDetector("ar")
        service = DocumentLanguageService(db, detector)
        await service.ensure_detected(doc, GERMAN)
        await service.ensure_detected(doc, GERMAN, force=True)
        assert detector.calls == 2
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Precedence
# ---------------------------------------------------------------------------


def test_template_language_outranks_everything() -> None:
    assert (
        DocumentLanguageService.resolve(
            template_language="fr",
            persisted=DetectedLanguage("de", 0.9, "local"),
            provider_detected="en",
        )
        == "fr"
    )


def test_persisted_detection_outranks_provider_metadata() -> None:
    """The dedicated detector sees the whole document; a translation provider
    only sees whatever happened to be translated."""
    assert (
        DocumentLanguageService.resolve(
            persisted=DetectedLanguage("de", 0.9, "local"), provider_detected="en"
        )
        == "de"
    )


@pytest.mark.parametrize("real", ["de", "ar", "fr"])
def test_a_real_detection_is_never_overwritten_by_en(real: str) -> None:
    """The exact reported bug: a provider's assumed `en` replacing a real
    answer."""
    assert (
        DocumentLanguageService.resolve(
            persisted=DetectedLanguage(real, 0.95, "local"), provider_detected="en"
        )
        == real
    )


def test_provider_metadata_is_used_when_nothing_better_exists() -> None:
    assert DocumentLanguageService.resolve(provider_detected="ar") == "ar"


def test_undetermined_when_nothing_is_known() -> None:
    assert DocumentLanguageService.resolve() == UNDETERMINED
    assert (
        DocumentLanguageService.resolve(
            persisted=DetectedLanguage(UNDETERMINED, 0.0, "local")
        )
        == UNDETERMINED
    )


def test_source_language_never_comes_from_user_or_output_language() -> None:
    """`resolve` has no parameter for either, by construction — the three
    language concepts stay separate."""
    import inspect

    parameters = set(inspect.signature(DocumentLanguageService.resolve).parameters)
    assert "user_language" not in parameters
    assert "output_language" not in parameters


# ---------------------------------------------------------------------------
# Mixed batches
# ---------------------------------------------------------------------------


def test_dominant_language_picks_the_most_frequent() -> None:
    assert dominant_language(("de", "de", "en")) == "de"


def test_dominant_language_ignores_und() -> None:
    assert dominant_language(("und", "und", "ar")) == "ar"


def test_dominant_language_breaks_ties_alphabetically() -> None:
    """Deterministic, so the same document always yields the same answer."""
    assert dominant_language(("en", "de")) == "de"
    assert dominant_language(("de", "en")) == "de"


def test_dominant_language_of_nothing_is_und() -> None:
    assert dominant_language(()) == UNDETERMINED
    assert dominant_language(("und",)) == UNDETERMINED


# ---------------------------------------------------------------------------
# Sampling
# ---------------------------------------------------------------------------


def test_sample_excludes_identifiers() -> None:
    sample = build_language_sample(
        "Vermieter Name\nDE89 3704 0044 0532 0130 00\nuser@example.com\n"
        "2026-07-30\n+49 30 12345678\nMieter Name"
    )
    assert "Vermieter Name" in sample
    assert "DE89" not in sample
    assert "user@example.com" not in sample
    assert "2026-07-30" not in sample


def test_sample_is_bounded() -> None:
    sample = build_language_sample("Der Vertrag ist gültig. " * 5000)
    assert len(sample) <= 5000


def test_sample_deduplicates_repeated_lines() -> None:
    sample = build_language_sample("Unterschrift\nUnterschrift\nUnterschrift")
    assert sample.count("Unterschrift") == 1


def test_has_enough_text_requires_real_words() -> None:
    assert has_enough_text("one two three four five six seven eight") is True
    assert has_enough_text("Name") is False
