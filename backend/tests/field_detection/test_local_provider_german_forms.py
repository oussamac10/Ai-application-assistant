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


def _word_tokens(
    words: list[tuple[str, float]], y: float = 200, height: float = 14
) -> tuple[DetectionToken, ...]:
    """Builds one token per word at explicit x positions, mirroring how
    PyMuPDF's `get_text("words")` actually reports a line — the inline-blank
    detector measures the gap between adjacent *word* tokens, so a test
    fixture must not lump a whole phrase into one token."""
    return tuple(
        _token(text, x=x, y=y, width=max(len(text) * 5.0, 4.0), height=height)
        for text, x in words
    )


def test_sentence_embedded_date_fields_are_detected() -> None:
    # "Das Vertragsverhältnis beginnt am ____ und endet am ____ ." — the two
    # blanks are pure whitespace, marked only by a wide gap after "am".
    tokens = _word_tokens(
        [
            ("Das", 40),
            ("Vertragsverhältnis", 62),
            ("beginnt", 160),
            ("am", 200),
            # wide blank gap (>1.2 x 14pt height) before "und"
            ("und", 280),
            ("endet", 300),
            ("am", 330),
            # wide blank gap before the final full stop
            (".", 420),
        ]
    )
    result = LocalFieldDetectionProvider().detect(_single_page_document(tokens))

    date_fields = [f for f in result.fields if f.field_type == "date"]
    assert len(date_fields) == 2
    assert any(f.label.endswith("beginnt am") for f in date_fields)
    assert any(f.label.endswith("endet am") for f in date_fields)
    # Page number and both bounding boxes are preserved for later mapping.
    for field in date_fields:
        assert field.page_number == 1
        assert field.label_bounding_box is not None
        assert field.input_bounding_box is not None


def test_sentence_embedded_amount_field_is_detected() -> None:
    # "Die monatliche Grundmiete beträgt ____ Euro."
    tokens = _word_tokens(
        [
            ("Die", 40),
            ("monatliche", 62),
            ("Grundmiete", 130),
            ("beträgt", 200),
            # wide blank gap before the currency unit
            ("Euro.", 300),
        ]
    )
    result = LocalFieldDetectionProvider().detect(_single_page_document(tokens))

    currency_fields = [f for f in result.fields if f.field_type == "currency"]
    assert len(currency_fields) == 1
    assert "beträgt" in currency_fields[0].label


def test_sentence_embedded_euro_symbol_amount_is_detected() -> None:
    # "Die Mietzahlung in Höhe von insgesamt ____ € wird monatlich ..."
    tokens = _word_tokens(
        [
            ("Die", 40),
            ("Mietzahlung", 62),
            ("in", 130),
            ("Höhe", 150),
            ("von", 180),
            ("insgesamt", 210),
            ("€", 300),
            ("wird", 320),
            ("monatlich", 350),
        ]
    )
    result = LocalFieldDetectionProvider().detect(_single_page_document(tokens))

    currency_fields = [f for f in result.fields if f.field_type == "currency"]
    assert len(currency_fields) == 1
    assert "insgesamt" in currency_fields[0].label


def test_sentence_embedded_person_count_is_detected() -> None:
    # "In den vermieteten Räumlichkeiten sind ____ Personen untergebracht."
    tokens = _word_tokens(
        [
            ("In", 40),
            ("den", 58),
            ("vermieteten", 85),
            ("Räumlichkeiten", 150),
            ("sind", 230),
            ("Personen", 320),
            ("untergebracht.", 380),
        ]
    )
    result = LocalFieldDetectionProvider().detect(_single_page_document(tokens))

    number_fields = [f for f in result.fields if f.field_type == "number"]
    assert len(number_fields) == 1
    assert "Personen" in number_fields[0].label


def test_normal_word_spacing_never_produces_an_inline_blank_field() -> None:
    """Ordinary prose containing a date preposition must not become a field
    just because the trigger word is present — the wide gap is required."""
    tokens = _word_tokens(
        [
            ("Der", 40),
            ("Vertrag", 62),
            ("endet", 105),
            ("am", 135),
            # normal word spacing (~0.2x height), not a blank
            ("Monatsende", 155),
            ("automatisch.", 215),
        ]
    )
    result = LocalFieldDetectionProvider().detect(_single_page_document(tokens))
    assert [f for f in result.fields if f.field_type == "date"] == []


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
    """A faithful synthetic equivalent of the real
    Jobcenter-LK-SM-Muster-Mietvertrag-Zimmer.pdf, reproducing every layout
    trait that actually mattered for detection:

    - 3 pages, native text, no AcroForm widgets, not encrypted;
    - "Label:" and its Unicode dotted-leader input area rendered far enough
      apart to land in *separate* segments on the same physical line (this
      is what the real Word export does, and what the colon+blank-sibling
      rule handles);
    - underscore-run input areas for the bank block;
    - sentence-embedded blanks made of pure whitespace, at the real
      document's ~2.3x-line-height gap — deliberately below the
      segment-split threshold, as in the original;
    - the same short label repeated under a landlord and a tenant section,
      which must stay two distinct fields;
    - "§ N Titel" headings and a multi-line legal paragraph plus numbered
      footnotes, none of which may become fields.
    """
    dots = "…" * 25
    underscores = "_" * 40

    c = canvas.Canvas(filepath, pagesize=A4)

    # --- page 1: parties (repeated labels) + property + person count -----
    _draw(c, 780, "Mietvertrag", size=14)
    _draw(c, 750, "Zwischen dem Vermieter")
    for y, label in ((720, "Name:"), (700, "Straße, Nr.:"), (680, "PLZ, Ort:")):
        _draw(c, y, label)
        _draw(c, y, dots, x=200)  # separate segment on the same line
    _draw(c, 640, "und dem Mieter")
    for y, label in ((610, "Name:"), (590, "Straße, Nr.:"), (570, "PLZ, Ort:")):
        _draw(c, y, label)
        _draw(c, y, dots, x=200)
    _draw(c, 530, "wird folgender Mietvertrag geschlossen:")
    _draw(c, 500, "§ 1 Mietraum / Mieträume", size=11)
    _draw(c, 480, "Im Haus (Ort, Straße, Haus-Nr., Etage)")
    _draw(c, 480, dots, x=250)
    _draw(c, 450, "§ 2 Anzahl der untergebrachten Personen", size=11)
    # whitespace blank: "sind ____ Personen" (gap ~32pt at ~13.6pt height)
    _draw(c, 430, "In den vermieteten Räumlichkeiten sind")
    _draw(c, 430, "Personen untergebracht.", x=250)
    _draw(c, 60, "Seite 1 von 3", size=8)
    c.showPage()

    # --- page 2: dates + amounts (whitespace blanks) + bank block --------
    _draw(c, 780, "§ 3 Mietdauer", size=11)
    _draw(c, 755, "Das Vertragsverhältnis beginnt am")
    _draw(c, 755, "und endet am", x=250)
    _draw(c, 755, ".", x=350)
    _draw(c, 730, "Beginn des Mietvertrages ist der")
    _draw(c, 730, ".", x=250)
    _draw(c, 700, "§ 4 Mietkosten", size=11)
    _draw(c, 675, "Die monatliche Grundmiete beträgt")
    _draw(c, 675, "Euro.", x=250)
    _draw(c, 655, "Die monatliche Betriebskostenvorauszahlung beträgt")
    _draw(c, 655, "Euro.", x=320)
    _draw(c, 635, "Die monatliche Heizkostenvorauszahlung beträgt")
    _draw(c, 635, "Euro.", x=310)
    _draw(c, 610, "Die Mietzahlung in Höhe von insgesamt")
    _draw(c, 610, "€ wird monatlich gezahlt auf:", x=280)
    for y, label in (
        (570, "Kontoinhaber:"),
        (550, "Bank:"),
        (530, "IBAN:"),
        (510, "BIC:"),
    ):
        _draw(c, y, label)
        _draw(c, y, underscores, x=200)
    # Numbered footnotes in the bottom margin — never fields.
    _draw(
        c,
        120,
        "1 Betriebskosten werden ohne Strom erhoben. Stromabschläge sind",
        size=8,
    )
    _draw(c, 110, "durch den Mieter eigenverantwortlich zu zahlen.", size=8)
    _draw(c, 60, "Seite 2 von 3", size=8)
    c.showPage()

    # --- page 3: legal prose (must be ignored) + signatures -------------
    _draw(c, 780, "§ 5 Mängel und Schäden an der Wohnung", size=11)
    _draw(
        c,
        755,
        "1. Zeigt sich in der Wohnung bzw. den überlassenen Räumlichkeiten ein",
        size=9,
    )
    _draw(
        c,
        744,
        "Mangel, so muss dies der Mieter dem Vermieter unverzüglich mitteilen.",
        size=9,
    )
    _draw(
        c,
        720,
        "2. Hat die Wohnung einen nicht unerheblichen Mangel oder fehlt bzw.",
        size=9,
    )
    _draw(
        c, 709, "entfällt eine zugesicherte Eigenschaft, so kann der Mieter in", size=9
    )
    _draw(
        c,
        698,
        "angemessenem Umfang die Miete kürzen, bis der Vermieter den Mangel",
        size=9,
    )
    _draw(c, 687, "abstellt. Weitere Ansprüche bleiben bestehen.", size=9)
    _draw(c, 650, "§ 6 Kündigungsfrist", size=11)
    _draw(
        c,
        630,
        "Der Mietvertrag kann durch beide Vertragsparteien mit einer Frist von",
        size=9,
    )
    _draw(c, 619, "4 Wochen zum Monatsende gekündigt werden.", size=9)
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
    keys = {f.normalized_name for f in usable}

    # Far more than the "at least five usable questions" bar.
    assert len(usable) >= 15

    # The landlord's and the tenant's identically-labelled fields both
    # survive as distinct fields (the whole point of section context).
    assert "vermieter_name" in keys
    assert "mieter_name" in keys
    assert "Vermieter – Name" in labels
    assert "Mieter – Name" in labels

    # Bank block (underscore input areas).
    assert "IBAN" in labels
    assert "BIC" in labels
    assert "Kontoinhaber" in labels
    assert "Bank" in labels

    # No decorative dots-only or bare-heading candidate ever appears.
    assert not any(set(label.strip()) <= {"…", " "} for label in labels)
    assert not any(label.startswith("§") for label in labels)

    # Legal prose, footnotes and the colon-terminated linking sentence are
    # never turned into fields.
    for forbidden in (
        "wird folgender Mietvertrag geschlossen",
        "Betriebskosten werden ohne Strom erhoben",
        "Der Mietvertrag kann durch beide Vertragsparteien",
        "Zeigt sich in der Wohnung",
    ):
        assert not any(forbidden in label for label in labels), forbidden


def test_rental_contract_fixture_covers_every_required_field_type(
    tmp_path: Path,
) -> None:
    """Every field this document must be able to ask about, with the
    field type its label/context deterministically implies."""
    pdf_path = tmp_path / "rental-contract.pdf"
    build_rental_contract_fixture_pdf(str(pdf_path))

    result = LocalFieldDetectionProvider().detect(
        extract_native_document_input(pdf_path)
    )
    by_key = {f.normalized_name: f for f in result.fields}

    expectations = {
        "vermieter_name": "text",
        "vermieter_stra_e_nr": "address",
        "vermieter_plz_ort": "address",
        "mieter_name": "text",
        "mieter_stra_e_nr": "address",
        "im_haus": "address",
        "personen": "number",
        "beginnt_am": "date",
        "endet_am": "date",
        "ist_der": "date",
        "grundmiete": "currency",
        "insgesamt": "currency",
        "kontoinhaber": "text",
        "bank": "text",
        "iban": "text",
        "bic": "text",
    }
    for fragment, expected_type in expectations.items():
        field = next((f for k, f in by_key.items() if fragment in k), None)
        assert field is not None, f"missing field for {fragment!r}"
        assert (
            field.field_type == expected_type
        ), f"{fragment}: expected {expected_type}, got {field.field_type}"


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

        # Keys are section-prefixed so the landlord's and tenant's
        # identically-labelled "Name:" fields stay distinct (sections.py).
        field_keys = {f.key for f in version.fields}
        assert "vermieter_name" in field_keys
        assert "mieter_name" in field_keys
        assert any("iban" in k for k in field_keys)
        assert any("bic" in k for k in field_keys)
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
        assert "vermieter_name_vermieter" in field_keys
        assert "vermieter_iban" in field_keys
        assert not any("xyz" in k for k in field_keys)
    finally:
        db.close()
