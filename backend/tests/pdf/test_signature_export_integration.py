"""Signatures through the real export pipeline, verified in the output PDF.

`test_signature_render.py` covers the renderer in isolation. These tests run the
renderer the way production does — via `PypdfRenderer.render`, filling AcroForm
fields first and drawing afterwards — and then reopen the written file to check
what actually landed on the page.

That distinction matters. A renderer can be perfect and still never be called,
which is exactly the state this work found the code in: the signature renderer
existed, was fully tested, and the export path filled form fields only.
"""

from __future__ import annotations

from pathlib import Path

import fitz
import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.answers.signatures import PENDING_MANUAL_SIGNATURE
from app.pdf.renderers.pypdf_renderer import PypdfRenderer
from app.pdf.schemas import PDFFieldMapping, PDFTemplateMapping
from app.pdf.signature_render import (
    SIGNATURE_INVALID,
    SignatureBox,
    SignatureRenderError,
    should_render_signature,
)

# A signature area big enough to measure against, placed away from the text so
# a stray drawing is unambiguous.
_BOX = SignatureBox(page_number=1, x=72.0, y=560.0, width=220.0, height=70.0)

_STROKES = {
    "strokes": [[[0.0, 0.0], [120.0, 60.0], [240.0, 10.0]]],
    "width": 300.0,
    "height": 100.0,
}


@pytest.fixture
def template(tmp_path: Path) -> Path:
    """A small form with one AcroForm text field and printed body text."""
    path = tmp_path / "template.pdf"
    c = canvas.Canvas(str(path), pagesize=letter)
    c.drawString(72, 720, "Antrag auf Erteilung")
    c.drawString(72, 700, "Unterschrift des Antragstellers:")
    c.acroForm.textfield(
        name="applicant_name", x=72, y=660, width=220, height=18, value=""
    )
    c.showPage()
    # A second page, so "unrelated pages are untouched" is testable.
    c.drawString(72, 720, "Seite zwei")
    c.showPage()
    c.save()
    return path


def _mapping(signature_rect: list[float] | None = None) -> PDFTemplateMapping:
    fields = [
        PDFFieldMapping(
            fieldKey="applicant_name",
            pdfFieldName="applicant_name",
            format="text",
        ),
    ]
    if signature_rect is not None:
        fields.append(
            PDFFieldMapping(
                fieldKey="signature",
                pdfFieldName="signature",
                format="text",
                page=1,
                signatureRect=signature_rect,
            )
        )
    return PDFTemplateMapping(
        templateKey="t", formVersionKey="v", mappingVersion=1, fields=fields
    )


def _ink_on(page) -> list[tuple[float, float]]:
    """Every point the renderer drew, ignoring the form's own printed content.

    Text and widget borders are not `drawings`, so what remains is signature
    ink — which is what lets a test say "the box is blank" and mean it.
    """
    points: list[tuple[float, float]] = []
    for drawing in page.get_drawings():
        for item in drawing["items"]:
            for element in item[1:]:
                if hasattr(element, "x") and hasattr(element, "y"):
                    points.append((element.x, element.y))
    return points


def _ink_in_box(page, box: SignatureBox) -> list[tuple[float, float]]:
    return [
        (x, y)
        for x, y in _ink_on(page)
        if box.x <= x <= box.x + box.width and box.y <= y <= box.y + box.height
    ]


# ---------------------------------------------------------------------------
# A: a digitally signed export
# ---------------------------------------------------------------------------


def test_a_digital_signature_reaches_the_exported_pdf(
    template: Path, tmp_path: Path
) -> None:
    """The whole point: the renderer is actually called by the export path."""
    output = tmp_path / "signed.pdf"

    PypdfRenderer().render(
        template_path=template,
        output_path=output,
        mapping=_mapping([72.0, 560.0, 220.0, 70.0]),
        values={"applicant_name": "Dupont"},
        signatures=[(_BOX, _STROKES)],
    )

    document = fitz.open(output)
    try:
        ink = _ink_in_box(document[0], _BOX)
        assert ink, "no signature ink landed inside the mapped rectangle"
        # Nothing escaped the box.
        assert len(ink) == len(_ink_on(document[0]))
    finally:
        document.close()


def test_the_signature_keeps_its_shape_in_the_export(
    template: Path, tmp_path: Path
) -> None:
    output = tmp_path / "signed.pdf"

    PypdfRenderer().render(
        template_path=template,
        output_path=output,
        mapping=_mapping([72.0, 560.0, 220.0, 70.0]),
        values={},
        signatures=[(_BOX, _STROKES)],
    )

    document = fitz.open(output)
    try:
        ink = _ink_in_box(document[0], _BOX)
        width = max(x for x, _ in ink) - min(x for x, _ in ink)
        height = max(y for _, y in ink) - min(y for _, y in ink)
        # Source ink spans 240 x 60; a stretched signature is not the one the
        # person drew.
        assert width / height == pytest.approx(240.0 / 60.0, rel=0.05)
    finally:
        document.close()


def test_normal_form_fields_still_export_alongside_a_signature(
    template: Path, tmp_path: Path
) -> None:
    """Drawing must not disturb the field-filling pass that ran before it."""
    output = tmp_path / "signed.pdf"

    PypdfRenderer().render(
        template_path=template,
        output_path=output,
        mapping=_mapping([72.0, 560.0, 220.0, 70.0]),
        values={"applicant_name": "Dupont"},
        signatures=[(_BOX, _STROKES)],
    )

    document = fitz.open(output)
    try:
        values = {
            widget.field_name: widget.field_value for widget in document[0].widgets()
        }
        assert values.get("applicant_name") == "Dupont"
    finally:
        document.close()


def test_the_forms_own_content_survives_the_signature_pass(
    template: Path, tmp_path: Path
) -> None:
    output = tmp_path / "signed.pdf"

    PypdfRenderer().render(
        template_path=template,
        output_path=output,
        mapping=_mapping([72.0, 560.0, 220.0, 70.0]),
        values={},
        signatures=[(_BOX, _STROKES)],
    )

    document = fitz.open(output)
    try:
        assert "Unterschrift des Antragstellers" in document[0].get_text()
        # An unrelated page is untouched.
        assert "Seite zwei" in document[1].get_text()
        assert _ink_on(document[1]) == []
    finally:
        document.close()


# ---------------------------------------------------------------------------
# B: sign after printing
# ---------------------------------------------------------------------------


def test_the_manual_sign_path_leaves_the_signature_area_blank(
    template: Path, tmp_path: Path
) -> None:
    """Intentionally blank. The box is left exactly as the form's author drew
    it — no placeholder, no stamp — because this document is about to be handed
    to an authority."""
    output = tmp_path / "manual.pdf"

    # The service omits a deferred signature entirely, which is what this
    # asserts at the renderer boundary.
    assert should_render_signature(PENDING_MANUAL_SIGNATURE) is False

    PypdfRenderer().render(
        template_path=template,
        output_path=output,
        mapping=_mapping([72.0, 560.0, 220.0, 70.0]),
        values={"applicant_name": "Dupont"},
        signatures=[],
    )

    document = fitz.open(output)
    try:
        assert _ink_in_box(document[0], _BOX) == []
        # The export still succeeded and still carries the other answers.
        assert "Unterschrift des Antragstellers" in document[0].get_text()
        values = {
            widget.field_name: widget.field_value for widget in document[0].widgets()
        }
        assert values.get("applicant_name") == "Dupont"
    finally:
        document.close()


# ---------------------------------------------------------------------------
# D: a signature that cannot be rendered
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        {"strokes": [[[float("nan"), 1.0]]], "width": 100.0, "height": 100.0},
        {"strokes": [[[float("inf"), 1.0]]], "width": 100.0, "height": 100.0},
        {"strokes": [[[9999.0, 1.0]]], "width": 100.0, "height": 100.0},
        {"strokes": [[["x", 1.0]]], "width": 100.0, "height": 100.0},
    ],
)
def test_a_malformed_signature_is_rejected_at_export(
    template: Path, tmp_path: Path, payload
) -> None:
    with pytest.raises(SignatureRenderError) as exc:
        PypdfRenderer().render(
            template_path=template,
            output_path=tmp_path / "bad.pdf",
            mapping=_mapping([72.0, 560.0, 220.0, 70.0]),
            values={},
            signatures=[(_BOX, payload)],
        )

    assert exc.value.error_code == SIGNATURE_INVALID


def test_an_export_error_never_carries_signature_coordinates(
    template: Path, tmp_path: Path
) -> None:
    with pytest.raises(SignatureRenderError) as exc:
        PypdfRenderer().render(
            template_path=template,
            output_path=tmp_path / "bad.pdf",
            mapping=_mapping([72.0, 560.0, 220.0, 70.0]),
            values={},
            signatures=[
                (_BOX, {"strokes": [[[4242.0, 3131.0]]], "width": 10.0, "height": 10.0})
            ],
        )

    message = str(exc.value)
    assert "4242" not in message
    assert "3131" not in message


def test_a_signature_page_outside_the_document_is_refused(
    template: Path, tmp_path: Path
) -> None:
    """Better to refuse than to write a signature onto the wrong page."""
    with pytest.raises(SignatureRenderError):
        PypdfRenderer().render(
            template_path=template,
            output_path=tmp_path / "bad.pdf",
            mapping=_mapping([72.0, 560.0, 220.0, 70.0]),
            values={},
            signatures=[
                (
                    SignatureBox(
                        page_number=99, x=72.0, y=560.0, width=220.0, height=70.0
                    ),
                    _STROKES,
                )
            ],
        )


def test_signature_export_logs_no_coordinates(
    template: Path, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("INFO"):
        PypdfRenderer().render(
            template_path=template,
            output_path=tmp_path / "signed.pdf",
            mapping=_mapping([72.0, 560.0, 220.0, 70.0]),
            values={},
            signatures=[(_BOX, _STROKES)],
        )

    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert "strokes=1" in logged
    assert "[[0.0, 0.0]" not in logged
    assert "240.0" not in logged


# ---------------------------------------------------------------------------
# C: no mapped signature area
# ---------------------------------------------------------------------------


class _Answer:
    def __init__(self, status: str, value: object) -> None:
        self.status = status
        self.normalized_value = value


def test_a_signature_with_no_mapped_rectangle_is_refused() -> None:
    """`domain-rules.md` forbids coordinate guessing, and a signature in the
    wrong part of an official form is worse than an export that declines to
    place it. There is deliberately no fallback position."""
    from app.pdf.services import _signature_box_for
    from app.pdf.signature_render import SIGNATURE_MAPPING_MISSING

    field_map = PDFFieldMapping(
        fieldKey="signature", pdfFieldName="signature", format="text"
    )

    with pytest.raises(SignatureRenderError) as exc:
        _signature_box_for(field_map, _Answer("confirmed", _STROKES))

    assert exc.value.error_code == SIGNATURE_MAPPING_MISSING


def test_a_deferred_signature_needs_no_mapping_at_all() -> None:
    """Nothing is drawn, so nothing has to be located — a template without a
    mapped signature area still exports for someone signing on paper."""
    from app.pdf.services import _signature_box_for

    field_map = PDFFieldMapping(
        fieldKey="signature", pdfFieldName="signature", format="text"
    )

    assert (
        _signature_box_for(field_map, _Answer(PENDING_MANUAL_SIGNATURE, None)) is None
    )


def test_a_mapped_signature_resolves_to_its_rectangle() -> None:
    from app.pdf.services import _signature_box_for

    field_map = PDFFieldMapping(
        fieldKey="signature",
        pdfFieldName="signature",
        format="text",
        page=2,
        signatureRect=[10.0, 20.0, 200.0, 60.0],
    )

    resolved = _signature_box_for(field_map, _Answer("confirmed", _STROKES))

    assert resolved is not None
    box, payload = resolved
    assert (box.page_number, box.x, box.y, box.width, box.height) == (
        2,
        10.0,
        20.0,
        200.0,
        60.0,
    )
    assert payload == _STROKES
