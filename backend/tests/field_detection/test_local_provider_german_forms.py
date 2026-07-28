"""Regression tests for the "no usable questions" failure on the German
rental-contract PDF (Jobcenter-LK-SM-Muster-Mietvertrag-Zimmer.pdf).

Root cause: the local field detector only recognized a field label when it
was terminated by a literal colon on the same line. Real German
bureaucratic forms commonly use Unicode dotted leaders ("…………"),
underscore runs ("________"), or a label on its own line with the blank
input area directly below it — none of which include a colon — and some
values (contract start/end date, monthly rent) are left blank in the
middle of a prose sentence rather than on a labeled line at all. Every
detected candidate was therefore silently skipped, and with zero usable
candidates, Phase 13's automatic flow correctly (but unhelpfully) reported
"no usable questions".
"""

from __future__ import annotations

from pathlib import Path

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.field_detection.confidence import decide_auto_review_status
from app.field_detection.extraction import extract_native_document_input
from app.field_detection.providers.base import (
    BoundingBox,
    DetectionDocumentInput,
    DetectionPageInput,
    DetectionToken,
)
from app.field_detection.providers.local import LocalFieldDetectionProvider


def _token(
    text: str,
    x: float,
    y: float,
    width: float = 40,
    height: float = 14,
    source: str = "native",
) -> DetectionToken:
    return DetectionToken(
        text=text,
        confidence=1.0,
        bounding_box=BoundingBox(x=x, y=y, width=width, height=height),
        source=source,
    )


def _single_page_document(tokens: tuple[DetectionToken, ...]) -> DetectionDocumentInput:
    return DetectionDocumentInput(
        page_count=1,
        pages=(
            DetectionPageInput(page_number=1, width=612, height=792, tokens=tokens),
        ),
    )


# ---------------------------------------------------------------------------
# Unicode dotted leader / underscore blank-run detection
# ---------------------------------------------------------------------------


def test_unicode_dotted_leader_label_without_colon_is_detected() -> None:
    tokens = (
        _token("IBAN", x=40, y=200, width=32),
        _token("…" * 30, x=80, y=200, width=300),
    )
    result = LocalFieldDetectionProvider().detect(_single_page_document(tokens))

    assert len(result.fields) == 1
    field = result.fields[0]
    assert field.label == "IBAN"
    assert field.normalized_name == "iban"
    # A blank-run marker is real layout evidence, not just weak guessing.
    assert field.confidence >= 0.55
    # The dots are a placeholder, never surfaced as a prefilled value.
    assert field.existing_value is None


def test_underscore_run_label_without_colon_is_detected() -> None:
    tokens = (
        _token("BIC", x=40, y=200, width=24),
        _token("_" * 30, x=70, y=200, width=250),
    )
    result = LocalFieldDetectionProvider().detect(_single_page_document(tokens))

    assert len(result.fields) == 1
    assert result.fields[0].label == "BIC"
    assert result.fields[0].existing_value is None


def test_dotted_leader_with_colon_still_works() -> None:
    """The pre-existing colon-based path is unaffected."""
    tokens = (
        _token("Name:", x=40, y=200, width=40),
        _token("…" * 30, x=90, y=200, width=300),
    )
    result = LocalFieldDetectionProvider().detect(_single_page_document(tokens))

    assert len(result.fields) == 1
    assert result.fields[0].label == "Name"
    assert result.fields[0].existing_value is None


def test_mixed_blank_run_characters_all_recognized() -> None:
    for blank in ["." * 10, "…" * 10, "·" * 10, "_" * 10, "-" * 10, ". . . . . ."]:
        tokens = (
            _token("Kontoinhaber", x=40, y=200, width=90),
            _token(blank, x=140, y=200, width=200),
        )
        result = LocalFieldDetectionProvider().detect(_single_page_document(tokens))
        assert len(result.fields) == 1, f"blank marker {blank!r} was not recognized"
        assert result.fields[0].label == "Kontoinhaber"


def test_short_punctuation_is_never_treated_as_a_blank_run() -> None:
    """Two or fewer dots/underscores is ordinary punctuation (e.g. an
    ellipsis at the end of a truncated heading), never a fillable blank."""
    tokens = (_token("Fortsetzung ..", x=40, y=200, width=90),)
    result = LocalFieldDetectionProvider().detect(_single_page_document(tokens))
    assert len(result.fields) == 0


# ---------------------------------------------------------------------------
# Label-above, blank-line-below layout
# ---------------------------------------------------------------------------


def test_label_on_its_own_line_above_a_blank_line_is_detected() -> None:
    # BoundingBox.y follows PyMuPDF's top-left-origin convention (y grows
    # downward), so the label's line has the *smaller* y and the blank
    # line directly below it has the *larger* y.
    tokens = (
        _token("Straße, Nr.", x=40, y=185, width=90),
        _token("…" * 30, x=40, y=200, width=300),
    )
    result = LocalFieldDetectionProvider().detect(_single_page_document(tokens))

    assert len(result.fields) == 1
    field = result.fields[0]
    assert field.label == "Straße, Nr."
    assert field.field_type == "address"


def test_label_above_far_blank_line_is_not_linked() -> None:
    """A blank line far below (not "close below") must not be linked to an
    unrelated label — avoids inventing a field from coincidental layout."""
    tokens = (
        _token("Bemerkung", x=40, y=100, width=70),
        _token("…" * 30, x=40, y=700, width=300),
    )
    result = LocalFieldDetectionProvider().detect(_single_page_document(tokens))
    assert len(result.fields) == 0


# ---------------------------------------------------------------------------
# Sentence-embedded blanks (date / currency)
# ---------------------------------------------------------------------------


def test_sentence_embedded_date_fields_are_detected() -> None:
    tokens = (
        _token("Das Vertragsverhältnis beginnt am", x=40, y=200, width=180),
        _token("und endet am", x=280, y=200, width=80),
        _token(".", x=420, y=200, width=6),
    )
    result = LocalFieldDetectionProvider().detect(_single_page_document(tokens))

    date_fields = [f for f in result.fields if f.field_type == "date"]
    assert len(date_fields) == 2
    assert any("beginnt am" in f.label for f in date_fields)
    assert any("endet am" in f.label for f in date_fields)


def test_sentence_embedded_amount_field_is_detected() -> None:
    tokens = (
        _token("Die monatliche Grundmiete beträgt", x=40, y=200, width=190),
        _token("Euro.", x=280, y=200, width=40),
    )
    result = LocalFieldDetectionProvider().detect(_single_page_document(tokens))

    currency_fields = [f for f in result.fields if f.field_type == "currency"]
    assert len(currency_fields) == 1
    assert "beträgt" in currency_fields[0].label


def test_ordinary_prose_sentence_is_never_treated_as_a_field() -> None:
    """A plain sentence with normal word spacing (no blank-run marker, no
    large gap, no recognized trigger word) must never become a field."""
    tokens = (
        _token(
            "Zwischen den Parteien werden zusätzlich folgende Vereinbarungen",
            x=40,
            y=200,
            width=350,
        ),
        _token("getroffen", x=400, y=200, width=60),
    )
    result = LocalFieldDetectionProvider().detect(_single_page_document(tokens))
    assert len(result.fields) == 0


def test_long_colon_terminated_sentence_is_not_treated_as_a_field() -> None:
    """A prose sentence that happens to end in a colon (introducing a
    list) is not a short field label and must be excluded."""
    tokens = (
        _token(
            "Zwischen den Parteien gelten zusätzlich folgende Regelungen als bindend:",
            x=40,
            y=200,
            width=460,
        ),
    )
    result = LocalFieldDetectionProvider().detect(_single_page_document(tokens))
    assert len(result.fields) == 0


def test_section_heading_is_not_treated_as_a_field() -> None:
    tokens = (_token("1. Vertragsparteien", x=40, y=200, width=140),)
    result = LocalFieldDetectionProvider().detect(_single_page_document(tokens))
    assert len(result.fields) == 0


# ---------------------------------------------------------------------------
# German label classification
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label,expected_type",
    [
        ("Name Vermieter", "text"),
        ("Name Mieter", "text"),
        ("Straße, Nr.", "address"),
        ("PLZ, Ort", "address"),
        ("IBAN", "text"),
        ("BIC", "text"),
        ("Anzahl der Personen", "number"),
        ("Unterschrift Vermieter", "signature"),
        ("Unterschrift Mieter", "signature"),
        ("Geburtsdatum", "date"),
    ],
)
def test_german_label_classification(label: str, expected_type: str) -> None:
    from app.field_detection.classification import classify_label

    assert classify_label(label) == expected_type


def test_landlord_and_tenant_name_are_not_misclassified_as_currency() -> None:
    """Regression: "miete" is a substring of "Vermieter"/"Mieter" —
    keyword matching must not let German compounding turn a name field
    into a currency field."""
    from app.field_detection.classification import classify_label

    assert classify_label("Name Vermieter") != "currency"
    assert classify_label("Name Mieter") != "currency"
    assert classify_label("Unterschrift Vermieter") != "currency"


# ---------------------------------------------------------------------------
# Repeated landlord / tenant labels both survive deduplication
# ---------------------------------------------------------------------------


def test_repeated_but_distinctly_worded_landlord_tenant_labels_both_survive() -> None:
    tokens = (
        _token("Name Vermieter", x=40, y=700, width=100),
        _token("…" * 20, x=150, y=700, width=200),
        _token("Straße, Nr.", x=40, y=680, width=90),
        _token("…" * 20, x=140, y=680, width=200),
        _token("Name Mieter", x=40, y=660, width=90),
        _token("…" * 20, x=140, y=660, width=200),
        _token("Straße, Nr.", x=40, y=640, width=90),
        _token("…" * 20, x=140, y=640, width=200),
    )
    result = LocalFieldDetectionProvider().detect(_single_page_document(tokens))
    labels = [f.label for f in result.fields]
    assert "Name Vermieter" in labels
    assert "Name Mieter" in labels
    # Identically-worded "Straße, Nr." on both sides collapses to one
    # candidate under existing normalized-name deduplication — expected,
    # documented pre-existing behavior, not something this fix changes.
    assert labels.count("Straße, Nr.") == 1


# ---------------------------------------------------------------------------
# Full rental-contract-shaped PDF fixture
# ---------------------------------------------------------------------------


def _draw(c: canvas.Canvas, y: float, text: str, size: int = 10, x: float = 40) -> None:
    c.setFont("Helvetica", size)
    c.drawString(x, y, text)


def build_rental_contract_fixture_pdf(filepath: str) -> None:
    """A synthetic equivalent of Jobcenter-LK-SM-Muster-Mietvertrag-Zimmer.pdf:
    3 pages, native text, no AcroForm, Unicode dotted leaders, underscore
    runs, sentence-embedded date/amount blanks, repeated section labels,
    German umlauts."""
    dots = "…" * 32
    underscores = "_" * 32

    c = canvas.Canvas(filepath, pagesize=A4)

    _draw(c, 800, "Mietvertrag für ein Zimmer (Muster)", size=16)
    _draw(c, 780, "Jobcenter Landkreis – Musterformular", size=9)
    _draw(c, 750, "1. Vertragsparteien", size=12)
    _draw(c, 730, f"Name Vermieter {dots}")
    _draw(c, 710, f"Straße, Nr. {dots}")
    _draw(c, 690, f"PLZ, Ort {dots}")
    _draw(c, 660, f"Name Mieter {dots}")
    _draw(c, 640, f"Straße, Nr. {dots}")
    _draw(c, 620, f"PLZ, Ort {dots}")
    _draw(c, 590, "2. Mieträume")
    _draw(c, 570, f"Anschrift der vermieteten Wohnung {dots}")
    _draw(c, 550, f"Anzahl der Personen {dots}")
    _draw(c, 60, "Seite 1 von 3", size=8)
    c.showPage()

    _draw(c, 800, "3. Mietzeit", size=12)
    _draw(c, 780, "Das Vertragsverhältnis beginnt am")
    _draw(c, 400, "und endet am")
    c.setFont("Helvetica", 10)
    c.drawString(500, 780, ".")
    _draw(c, 750, "4. Miete", size=12)
    _draw(c, 730, "Die monatliche Grundmiete beträgt")
    c.drawString(320, 730, "Euro.")
    _draw(c, 700, f"Kontoinhaber {dots}")
    _draw(c, 680, f"Bank {dots}")
    _draw(c, 660, f"IBAN {underscores}")
    _draw(c, 640, f"BIC {underscores}")
    _draw(c, 60, "Seite 2 von 3", size=8)
    c.showPage()

    _draw(c, 800, "5. Unterschriften", size=12)
    _draw(c, 780, "Ort, Datum")
    _draw(c, 765, dots)
    _draw(c, 730, "Unterschrift Vermieter")
    _draw(c, 715, dots)
    _draw(c, 680, "Unterschrift Mieter")
    _draw(c, 665, dots)
    _draw(c, 60, "Seite 3 von 3", size=8)
    c.showPage()

    c.save()


def test_rental_contract_fixture_produces_many_usable_candidates(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "rental-contract.pdf"
    build_rental_contract_fixture_pdf(str(pdf_path))

    doc_input = extract_native_document_input(pdf_path)
    result = LocalFieldDetectionProvider().detect(doc_input)

    usable = [
        f
        for f in result.fields
        if decide_auto_review_status(f) != "needs_clarification"
    ]
    labels = {f.label for f in usable}

    assert len(usable) >= 10
    assert "Name Vermieter" in labels
    assert "Name Mieter" in labels
    assert "IBAN" in labels
    assert "BIC" in labels
    # No decorative dots-only or bare-heading candidate ever appears.
    assert not any(set(label.strip()) <= {"…", " "} for label in labels)


# ---------------------------------------------------------------------------
# End-to-end: orchestration produces a real, usable guided session
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rental_contract_reaches_a_real_guided_session(tmp_path: Path) -> None:
    """The exact reported failure, end-to-end: this document must no
    longer produce "no usable questions" — it must reach a real session
    with real fields, including the ones explicitly required by the task
    (landlord name, tenant name, IBAN, BIC, rent amount)."""
    from sqlalchemy import text as sa_text

    import app.main  # noqa: F401  registers every SQLAlchemy mapper once
    from app.ai.mock_provider import MockAIProvider
    from app.database.session import SessionLocal
    from app.documents.service import SourceDocumentService
    from app.field_detection.orchestration import PrepareQuestionsService
    from app.forms.repositories import FormRepository

    pdf_path = tmp_path / "rental-contract.pdf"
    build_rental_contract_fixture_pdf(str(pdf_path))

    db = SessionLocal()
    try:
        db.execute(sa_text("TRUNCATE TABLE source_documents CASCADE"))
        db.execute(sa_text("TRUNCATE TABLE form_templates CASCADE"))
        db.execute(sa_text("TRUNCATE TABLE form_sessions CASCADE"))
        db.commit()

        doc_service = SourceDocumentService(db)
        with open(pdf_path, "rb") as f:
            content = f.read()
        doc, token = doc_service.upload_and_analyze(
            filename="rental-contract.pdf",
            content_type="application/pdf",
            file_chunks=[content],
            privacy_accepted=True,
            user_language="de",
            output_language="de",
        )
        assert doc.analysis_result["next_step"] == "dynamic_field_detection"

        service = PrepareQuestionsService(
            db,
            ai_provider=MockAIProvider(),
            field_detection_provider=LocalFieldDetectionProvider(),
        )
        result = await service.prepare(doc.public_id, token, "de", "de")

        assert result.status == "ready"
        assert result.error_code is None
        assert result.session is not None

        version = FormRepository(db).get_version(result.session.form_version_id)
        assert version is not None
        assert len(version.fields) >= 8

        field_keys = {f.key for f in version.fields}
        assert "name_vermieter" in field_keys
        assert "name_mieter" in field_keys
        assert "iban" in field_keys
        assert "bic" in field_keys
    finally:
        db.close()


@pytest.mark.asyncio
async def test_one_unknown_type_candidate_does_not_block_the_others(
    tmp_path: Path,
) -> None:
    """An unsafe/unclassifiable candidate mixed in with clear fields must
    be excluded on its own, never fail the whole document."""
    from sqlalchemy import text as sa_text

    import app.main  # noqa: F401
    from app.ai.mock_provider import MockAIProvider
    from app.database.session import SessionLocal
    from app.documents.service import SourceDocumentService
    from app.field_detection.orchestration import PrepareQuestionsService
    from app.forms.repositories import FormRepository

    def build_pdf_with_one_ambiguous_line(filepath: str) -> None:
        c = canvas.Canvas(filepath, pagesize=A4)
        dots = "…" * 30
        _draw(c, 700, f"Name Vermieter {dots}")
        _draw(c, 680, f"IBAN {dots}")
        # A short, ambiguous fragment with no keyword match, no colon, no
        # blank-run marker, and no sentence-embedded trigger — never
        # becomes a candidate at all (safely excluded, not guessed at).
        _draw(c, 660, "xyz")
        c.showPage()
        c.save()

    pdf_path = tmp_path / "ambiguous.pdf"
    build_pdf_with_one_ambiguous_line(str(pdf_path))

    db = SessionLocal()
    try:
        db.execute(sa_text("TRUNCATE TABLE source_documents CASCADE"))
        db.execute(sa_text("TRUNCATE TABLE form_templates CASCADE"))
        db.execute(sa_text("TRUNCATE TABLE form_sessions CASCADE"))
        db.commit()

        doc_service = SourceDocumentService(db)
        with open(pdf_path, "rb") as f:
            content = f.read()
        doc, token = doc_service.upload_and_analyze(
            filename="ambiguous.pdf",
            content_type="application/pdf",
            file_chunks=[content],
            privacy_accepted=True,
            user_language="de",
            output_language="de",
        )

        service = PrepareQuestionsService(
            db,
            ai_provider=MockAIProvider(),
            field_detection_provider=LocalFieldDetectionProvider(),
        )
        result = await service.prepare(doc.public_id, token, "de", "de")

        assert result.status == "ready"
        assert result.session is not None
        version = FormRepository(db).get_version(result.session.form_version_id)
        field_keys = {f.key for f in version.fields}
        assert "name_vermieter" in field_keys
        assert "iban" in field_keys
        assert not any("xyz" in k for k in field_keys)
    finally:
        db.close()
