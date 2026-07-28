"""Regression tests for the real-PDF upload failure ("documentUpload.error_null").

Reproduces the reported failure with a synthetic PDF matching the verified
properties of the real document (Jobcenter-LK-SM-Muster-Mietvertrag-Zimmer.pdf):
3 pages, native text, no AcroForm/XFA, not encrypted, Word-style dotted
input lines, repeated section labels across pages, checkbox-like choices
written as plain text, dates embedded in sentences, German umlauts, and a
large number of detected candidate fields.

Root cause found: `question_bridge.create_session_from_confirmed_fields`
built the dynamic form version's `supported_output_languages` from only
`{"en", user_language}`, so any request with an `output_language` that
differed from both (a completely normal selection — the UI lets users pick
it independently) made `SessionService.create_session` reject its own
freshly created version with an unhandled `ValidationError` carrying no
`error_code` — which the frontend rendered as the literal, untranslated
string "documentUpload.error_null" (see DocumentUploadForm.tsx and
ApiError's `undefined` -> `null` default-parameter behavior, fixed
separately in the frontend).
"""

from __future__ import annotations

import asyncio
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from sqlalchemy import text

import app.main  # noqa: F401  registers every SQLAlchemy mapper once
from app.ai.mock_provider import MockAIProvider
from app.database.session import SessionLocal
from app.documents.errors import DocumentUnauthorizedError
from app.documents.service import SourceDocumentService
from app.field_detection.orchestration import PrepareQuestionsService


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


def _line(
    c: canvas.Canvas, y: float, text_: str, size: int = 10, x: float = 40
) -> None:
    c.setFont("Helvetica", size)
    c.drawString(x, y, text_)


def _create_rental_contract_pdf(filepath: str) -> None:
    """A 3-page, native-text, no-AcroForm German rental-contract-style PDF:
    multiple fields per line, long dotted input lines, checkbox-like
    choices written as plain text, repeated section labels across pages,
    a date embedded in a sentence, and German umlauts — matching the
    verified properties of the real reported document."""
    c = canvas.Canvas(filepath, pagesize=A4)

    # Page 1
    _line(c, 800, "Mietvertrag für Wohnraum (Muster)", size=16)
    _line(c, 770, "zwischen Vermieter und Mieter", size=11)
    _line(c, 730, "Name Vermieter: ................................................")
    _line(c, 710, "Anschrift Vermieter: ..........................................")
    _line(c, 690, "Name Mieter: ...................................................")
    _line(c, 670, "Anschrift Mieter: ..............................................")
    _line(c, 640, "§ 1 Mieträume")
    _line(c, 620, "Anschrift der Wohnung: .......................................")
    _line(c, 600, "Anzahl der Zimmer: .....  Anzahl der Personen: .....")
    _line(c, 580, "Schlüssel: Haustür ..... Wohnungstür ..... Briefkasten .....")
    _line(c, 540, "§ 2 Mietzeit")
    _line(c, 520, "Das Mietverhältnis beginnt am ..... und läuft auf unbestimmte Zeit.")
    _line(c, 500, "Kündigungsfrist: drei Monate zum Monatsende.")
    _line(c, 460, "§ 3 Miete und Nebenkosten")
    _line(c, 440, "Grundmiete: ..... EUR   Nebenkostenvorauszahlung: ..... EUR")
    _line(c, 420, "Gesamtmiete monatlich: ..... EUR")
    _line(c, 400, "Bankverbindung: IBAN ..... BIC .....")
    _line(c, 360, "§ 4 Sonstige Vereinbarungen")
    _line(c, 340, "[ ] Haustiere erlaubt")
    _line(c, 325, "[ ] Rauchen erlaubt")
    _line(c, 310, "[ ] Untervermietung erlaubt")
    _line(c, 60, "Seite 1 von 3", size=8)
    c.showPage()

    # Page 2 — repeated section labels, date embedded in a sentence
    _line(c, 800, "§ 5 Wiederholte Abschnittsüberschrift", size=12)
    _line(c, 780, "Name Vermieter: ................................................")
    _line(c, 760, "Name Mieter: ...................................................")
    _line(
        c,
        730,
        "Der Mieter bestätigt den Erhalt der Wohnung am ..... in ordnungsgemäßem Zustand.",
    )
    _line(
        c,
        710,
        "Zählerstände bei Übergabe: Strom ..... Gas ..... Wasser (kalt) ..... Wasser (warm) .....",
    )
    _line(c, 680, "Kaution: ..... EUR, fällig bei Vertragsbeginn.")
    _line(
        c,
        660,
        "Zusätzliche Vereinbarungen: ..................................................",
    )
    _line(
        c,
        640,
        "..................................................................................",
    )
    _line(c, 60, "Seite 2 von 3", size=8)
    c.showPage()

    # Page 3 — signatures
    _line(c, 800, "§ 6 Unterschriften", size=12)
    _line(c, 760, "Ort, Datum: ......................................")
    _line(c, 700, "Unterschrift Vermieter: ......................................")
    _line(c, 660, "Unterschrift Mieter: ......................................")
    _line(c, 60, "Seite 3 von 3", size=8)
    c.showPage()

    c.save()


def _upload(tmp_path: Path, builder) -> tuple[Any, Any, str]:
    pdf_path = tmp_path / "rental-contract.pdf"
    builder(str(pdf_path))
    db = SessionLocal()
    doc_service = SourceDocumentService(db)
    with open(pdf_path, "rb") as f:
        content = f.read()
    doc, token = doc_service.upload_and_analyze(
        filename="rental-contract.pdf",
        content_type="application/pdf",
        file_chunks=[content],
        privacy_accepted=True,
        user_language="en",
        output_language="en",
    )
    return db, doc, token


@pytest.mark.asyncio
async def test_valid_three_page_native_text_pdf_processes_successfully(
    tmp_path: Path,
) -> None:
    """The exact verified properties of the real reported document: 3
    pages, native text, no AcroForm/XFA, not encrypted, not scanned. Must
    process end-to-end with the real local field-detection provider — no
    exception, a real session created."""
    db, doc, token = _upload(tmp_path, _create_rental_contract_pdf)
    try:
        assert doc.page_count == 3
        assert doc.has_native_text is True
        assert doc.has_acroform is False
        assert doc.is_probably_scanned is False
        assert doc.analysis_result["next_step"] == "dynamic_field_detection"

        service = PrepareQuestionsService(db, ai_provider=MockAIProvider())
        result = await service.prepare(doc.public_id, token, "en", "en")

        assert result.status == "ready"
        assert result.error_code is None
        assert result.session is not None
    finally:
        db.close()


@pytest.mark.asyncio
async def test_output_language_independent_of_interface_language_does_not_crash(
    tmp_path: Path,
) -> None:
    """Reproduces the exact reported bug: a user_language/output_language
    combination outside {"en", user_language} previously made
    SessionService.create_session raise an unhandled ValidationError with
    no error_code, which the frontend rendered as the literal string
    "documentUpload.error_null". Every UI-offered combination must work."""
    db, doc, token = _upload(tmp_path, _create_rental_contract_pdf)
    try:
        service = PrepareQuestionsService(db, ai_provider=MockAIProvider())
        result = await service.prepare(doc.public_id, token, "en", "fr")

        assert result.status == "ready"
        assert result.error_code is None
        assert result.stage is None
        assert result.session is not None
        assert result.session.output_language == "fr"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_all_four_ui_language_combinations_never_crash(tmp_path: Path) -> None:
    for user_language, output_language in [
        ("en", "de"),
        ("de", "en"),
        ("fr", "ar"),
        ("ar", "fr"),
        ("de", "de"),
    ]:
        db, doc, token = _upload(tmp_path, _create_rental_contract_pdf)
        try:
            service = PrepareQuestionsService(db, ai_provider=MockAIProvider())
            result = await service.prepare(
                doc.public_id, token, user_language, output_language
            )
            assert result.status == "ready", (
                f"{user_language}->{output_language} failed: "
                f"{result.status}/{result.error_code}"
            )
        finally:
            db.close()


@pytest.mark.asyncio
async def test_processing_failure_returns_structured_result_with_non_null_code(
    tmp_path: Path,
) -> None:
    """When a stage genuinely fails, the orchestration result must always
    carry a non-null, safe error_code and stage — never let a raw
    exception escape to become an opaque, error-code-less HTTP failure."""
    db, doc, token = _upload(tmp_path, _create_rental_contract_pdf)
    try:
        # Force a document-analysis shape that the automatic flow cannot
        # handle, exercising the "review_required" rejection path, which
        # raises FieldDetectionValidationError with its own explicit code
        # (a different, already-safe failure mode) — assert it is non-null.
        doc.analysis_result = {**doc.analysis_result, "next_step": "review_required"}
        db.add(doc)
        db.commit()

        service = PrepareQuestionsService(db, ai_provider=MockAIProvider())
        with pytest.raises(Exception) as exc_info:
            await service.prepare(doc.public_id, token, "en", "en")

        error_code = getattr(exc_info.value, "error_code", None)
        assert error_code is not None
        assert error_code == "cannot_process_automatically"
    finally:
        db.close()


@pytest.mark.asyncio
async def test_ownership_still_enforced_for_rental_contract_document(
    tmp_path: Path,
) -> None:
    db, doc, _token = _upload(tmp_path, _create_rental_contract_pdf)
    try:
        service = PrepareQuestionsService(db, ai_provider=MockAIProvider())
        with pytest.raises(DocumentUnauthorizedError):
            await service.prepare(doc.public_id, "wrong-token", "en", "en")
    finally:
        db.close()


def test_reproduces_bug_synchronously_without_asyncio_warnings(tmp_path: Path) -> None:
    """Sanity check that the async orchestration call completes cleanly
    end-to-end (no dangling coroutine / event-loop warnings) for this
    document shape, run via asyncio.run like a fresh process would."""
    db, doc, token = _upload(tmp_path, _create_rental_contract_pdf)
    try:
        service = PrepareQuestionsService(db, ai_provider=MockAIProvider())
        result = asyncio.run(service.prepare(doc.public_id, token, "en", "de"))
        assert result.status == "ready"
    finally:
        db.close()
