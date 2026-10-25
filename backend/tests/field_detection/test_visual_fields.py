"""Text fields in flattened PDFs, where nothing marks an input but ink.

A form with AcroForm widgets says where its fields are. A flattened one does
not: an underline beneath a label and the rule under a heading are the same
drawing. So most of what these tests pin is *restraint* — a missing question is
recoverable, because the user can still fill the printed form, while an invented
one asks somebody for something the document never requested.

Fixtures are generated here rather than committed as binaries, so what each one
contains is readable in the test that uses it.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.field_detection.extraction import extract_native_document_input
from app.field_detection.providers.local import LocalFieldDetectionProvider
from app.field_detection.visual_fields import (
    detect_visual_fields,
    is_plausible_label,
)

_W, _H = A4


def _pdf(tmp_path: Path, draw) -> Path:
    path = tmp_path / "fixture.pdf"
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("Helvetica", 11)
    draw(c)
    c.showPage()
    c.save()
    return path


def _fields(path: Path):
    document = extract_native_document_input(path)
    found = []
    for page in document.pages:
        page_fields, _counts = detect_visual_fields(page)
        found.extend(page_fields)
    return found


# ---------------------------------------------------------------------------
# A–D: the patterns that should produce fields
# ---------------------------------------------------------------------------


def test_a_label_above_an_underline_becomes_one_field(tmp_path: Path) -> None:
    def draw(c):
        c.drawString(72, _H - 200, "First name")
        c.line(72, _H - 215, 300, _H - 215)

    fields = _fields(_pdf(tmp_path, draw))

    assert len(fields) == 1
    assert fields[0].label == "First name"
    assert fields[0].field_type == "text"
    assert fields[0].association == "above"


def test_a_label_beside_an_underline_becomes_one_field(tmp_path: Path) -> None:
    def draw(c):
        c.drawString(72, _H - 200, "First name:")
        c.line(150, _H - 202, 380, _H - 202)

    fields = _fields(_pdf(tmp_path, draw))

    assert len(fields) == 1
    assert fields[0].label.startswith("First name")
    # A label on the same row is unambiguous, so it is trusted more than one
    # inferred from vertical overlap.
    assert fields[0].association == "same_row"
    assert fields[0].review_required is False


def test_a_label_above_a_box_becomes_one_field(tmp_path: Path) -> None:
    def draw(c):
        c.drawString(72, _H - 200, "City")
        c.rect(72, _H - 235, 240, 24, stroke=1, fill=0)

    fields = _fields(_pdf(tmp_path, draw))

    assert len(fields) == 1
    assert fields[0].label == "City"
    assert fields[0].field_type == "text"


def test_a_tall_box_is_a_multiline_field(tmp_path: Path) -> None:
    def draw(c):
        c.drawString(72, _H - 200, "Remarks")
        c.rect(72, _H - 300, 400, 80, stroke=1, fill=0)

    fields = _fields(_pdf(tmp_path, draw))

    assert len(fields) == 1
    assert fields[0].field_type == "multiline_text"


def test_repeated_rows_stay_separate_and_ordered(tmp_path: Path) -> None:
    def draw(c):
        for index, label in enumerate(("First name", "Last name", "City")):
            y = _H - 200 - index * 40
            c.drawString(72, y, label)
            c.rect(72, y - 24, 240, 18, stroke=1, fill=0)

    fields = _fields(_pdf(tmp_path, draw))

    assert [f.label for f in fields] == ["First name", "Last name", "City"]
    # Three separate regions, never merged into one.
    assert len({(f.input_bounding_box.y) for f in fields}) == 3


# ---------------------------------------------------------------------------
# E–H: the things that must NOT produce fields
# ---------------------------------------------------------------------------


def test_a_decorative_rule_produces_nothing(tmp_path: Path) -> None:
    """A full-width rule divides the page. The French form draws exactly this
    under each page title, with a subtitle above it that reads enough like a
    label to be mistaken for one."""

    def draw(c):
        c.setFont("Helvetica-Bold", 16)
        c.drawString(72, _H - 80, "Application Form")
        c.line(40, _H - 95, _W - 40, _H - 95)

    assert _fields(_pdf(tmp_path, draw)) == []


def test_a_legal_paragraph_above_a_separator_produces_nothing(
    tmp_path: Path,
) -> None:
    def draw(c):
        c.setFont("Helvetica", 8)
        c.drawString(
            72,
            _H - 300,
            "Die Angaben werden gemaess Artikel 6 Absatz 1 der Verordnung "
            "verarbeitet und gespeichert.",
        )
        c.line(72, _H - 315, 460, _H - 315)

    # A sentence is prose, however close it sits to a rule.
    assert _fields(_pdf(tmp_path, draw)) == []


def test_a_box_that_already_contains_text_produces_nothing(
    tmp_path: Path,
) -> None:
    """A filled box is a printed cell — a header, a caption — not somewhere
    the user is being asked to write."""

    def draw(c):
        c.drawString(72, _H - 200, "Section")
        c.rect(72, _H - 240, 240, 30, stroke=1, fill=0)
        c.drawString(80, _H - 230, "Already printed here")

    assert _fields(_pdf(tmp_path, draw)) == []


def test_a_region_with_no_plausible_label_produces_nothing(
    tmp_path: Path,
) -> None:
    """Ambiguity resolves to silence. Inventing a question is worse than
    missing one, because the user can still fill the printed form."""

    def draw(c):
        c.rect(72, _H - 300, 300, 24, stroke=1, fill=0)

    fields = _fields(_pdf(tmp_path, draw))

    assert fields == []


def test_a_footer_rule_produces_nothing(tmp_path: Path) -> None:
    def draw(c):
        c.drawString(72, 46, "Page 1 / 2")
        c.line(72, 40, 300, 40)

    assert _fields(_pdf(tmp_path, draw)) == []


def test_a_signature_line_does_not_also_become_a_text_field(
    tmp_path: Path,
) -> None:
    """The signature classification is authoritative — a signature must not be
    asked for twice, once as ink and once as typing."""

    def draw(c):
        c.drawString(72, _H - 200, "Signature")
        c.line(72, _H - 215, 300, _H - 215)

    document = extract_native_document_input(_pdf(tmp_path, draw))
    candidates = LocalFieldDetectionProvider().detect(document).fields

    text_fields = [c for c in candidates if c.field_type in ("text", "string")]
    assert not any("signature" in c.label.lower() for c in text_fields)


# ---------------------------------------------------------------------------
# Label plausibility
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("First name", True),
        ("Nom de famille *", True),
        ("Date de naissance:", True),
        ("الاسم", True),
        # Rejected for length or for reading as a sentence — never for
        # containing a particular word.
        (
            "Die Angaben werden gemaess Artikel 6 Absatz 1 der Verordnung "
            "verarbeitet.",
            False,
        ),
        ("Please complete every field before signing this form.", False),
        ("", False),
        ("____", False),
        ("12", False),
    ],
)
def test_label_plausibility(text: str, expected: bool) -> None:
    assert is_plausible_label(text) is expected


def test_a_colon_survives_the_sentence_filter() -> None:
    """A trailing colon is the opposite of prose: it is a form asking."""
    assert is_plausible_label("Geburtsdatum:") is True
    assert is_plausible_label("Das ist ein Satz.") is False


def test_border_straddling_ocr_noise_taller_than_box_does_not_reject_empty_box() -> (
    None
):
    """Tesseract sometimes emits a low-confidence single-character artifact
    straddling the outer border of an empty input box (`height=146` on a `100px`
    box). Because no text printed *inside* a box can be taller than the box
    itself, `_contains_text` must ignore tokens taller than the box."""
    from app.field_detection.providers.base import (
        BoundingBox,
        DetectionPageInput,
        DetectionToken,
        RuledRegion,
    )

    page = DetectionPageInput(
        page_number=1,
        width=2480,
        height=3509,
        rotation=0,
        tokens=(
            DetectionToken(
                text="Aktuelle Anschrift *:",
                confidence=0.92,
                bounding_box=BoundingBox(x=231, y=1195, width=860, height=45),
                source="ocr",
            ),
            DetectionToken(
                text="р",
                confidence=0.40,
                bounding_box=BoundingBox(x=223, y=1257, width=256, height=146),
                source="ocr",
            ),
        ),
        ruled_regions=(
            RuledRegion(
                kind="box",
                page_number=1,
                bounding_box=BoundingBox(x=220, y=1261, width=2016, height=100),
            ),
        ),
    )

    fields, _ = detect_visual_fields(page)
    assert len(fields) == 1
    assert fields[0].label == "Aktuelle Anschrift *:"
