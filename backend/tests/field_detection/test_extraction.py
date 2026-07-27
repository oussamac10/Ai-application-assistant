from pathlib import Path

import pypdf
import pytest
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.field_detection.errors import FieldDetectionProviderUnavailableError
from app.field_detection.extraction import (
    extract_native_document_input,
    extract_ocr_document_input,
)
from app.ocr.models import OCRPage, OCRResult


def _create_digital_pdf(filepath: str) -> None:
    c = canvas.Canvas(filepath, pagesize=letter)
    c.drawString(100, 750, "Full Name")
    c.showPage()
    c.save()


def _create_acroform_pdf(filepath: str) -> None:
    c = canvas.Canvas(filepath, pagesize=letter)
    c.drawString(100, 630, "Email:")
    form = c.acroForm
    form.textfield(
        name="email", tooltip="email", x=200, y=620, width=200, height=20, value=""
    )
    c.showPage()
    c.save()


def _rotate_pdf(input_path: str, output_path: str, angle: int) -> None:
    reader = pypdf.PdfReader(input_path)
    writer = pypdf.PdfWriter()
    for page in reader.pages:
        page.rotate(angle)
        writer.add_page(page)
    with open(output_path, "wb") as f:
        writer.write(f)


def test_extract_native_document_input_returns_word_tokens(tmp_path: Path) -> None:
    pdf_path = tmp_path / "digital.pdf"
    _create_digital_pdf(str(pdf_path))

    result = extract_native_document_input(pdf_path)

    assert result.page_count == 1
    assert len(result.pages) == 1
    page = result.pages[0]
    assert page.page_number == 1
    assert page.rotation == 0
    texts = [t.text for t in page.tokens]
    assert "Full" in texts
    assert "Name" in texts
    assert all(t.source == "native" for t in page.tokens)
    assert all(t.confidence == 1.0 for t in page.tokens)


def test_extract_native_document_input_returns_acroform_widgets(tmp_path: Path) -> None:
    pdf_path = tmp_path / "acroform.pdf"
    _create_acroform_pdf(str(pdf_path))

    result = extract_native_document_input(pdf_path)

    assert len(result.acroform_widgets) == 1
    widget = result.acroform_widgets[0]
    assert widget.field_name == "email"
    assert widget.field_type == "text"
    assert widget.page_number == 1
    assert widget.rect.width > 0
    assert widget.rect.height > 0


def test_extract_native_document_input_reports_page_rotation(tmp_path: Path) -> None:
    pdf_path = tmp_path / "digital.pdf"
    rotated_path = tmp_path / "rotated.pdf"
    _create_digital_pdf(str(pdf_path))
    _rotate_pdf(str(pdf_path), str(rotated_path), 90)

    result = extract_native_document_input(rotated_path)

    assert result.pages[0].rotation == 90


def test_extract_native_document_input_raises_for_missing_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "does-not-exist.pdf"

    with pytest.raises(FieldDetectionProviderUnavailableError):
        extract_native_document_input(missing_path)


def test_extract_ocr_document_input_builds_tokens_from_ocr_pages() -> None:
    ocr_result = OCRResult(language="en")
    ocr_page = OCRPage(
        page_number=1,
        width=2480,
        height=3508,
        text="Full Name",
        average_confidence=95.0,
        lines=[
            {
                "text": "Full Name",
                "confidence": 95.0,
                "boundingBox": {"x": 100, "y": 200, "width": 300, "height": 40},
                "words": [
                    {
                        "text": "Full",
                        "confidence": 96.0,
                        "boundingBox": {"x": 100, "y": 200, "width": 140, "height": 40},
                    },
                    {
                        "text": "Name",
                        "confidence": 94.0,
                        "boundingBox": {"x": 250, "y": 200, "width": 150, "height": 40},
                    },
                ],
            }
        ],
    )
    ocr_result.pages = [ocr_page]

    result = extract_ocr_document_input(ocr_result)

    assert result.page_count == 1
    page = result.pages[0]
    assert page.width == 2480
    assert page.height == 3508
    assert len(page.tokens) == 2
    assert page.tokens[0].text == "Full"
    assert page.tokens[0].source == "ocr"
    assert page.tokens[0].confidence == pytest.approx(0.96)
    assert result.acroform_widgets == ()
    assert result.language == "en"


def _create_marker_pdf(filepath: str) -> None:
    """A checkbox (unfilled square), a radio control (unfilled circle,
    approximated by the PDF as Bezier curves), a filled banner rect, and a
    plain underline — only the checkbox and radio should synthesize marker
    tokens.
    """
    c = canvas.Canvas(filepath, pagesize=letter)
    c.setFont("Helvetica", 12)
    c.rect(0, 750, 612, 42, fill=1, stroke=0)  # filled banner, not a marker
    c.rect(100, 700, 12, 12, fill=0, stroke=1)  # checkbox
    c.drawString(120, 702, "Housing")
    c.circle(106, 660, 6, fill=0, stroke=1)  # radio
    c.drawString(120, 656, "Email")
    c.line(100, 600, 300, 600)  # underline, not a marker
    c.showPage()
    c.save()


def test_extract_native_document_input_synthesizes_checkbox_and_radio_markers(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "markers.pdf"
    _create_marker_pdf(str(pdf_path))

    result = extract_native_document_input(pdf_path)

    marker_texts = sorted(
        t.text for t in result.pages[0].tokens if t.text in ("[_]", "(_)")
    )
    assert marker_texts == ["(_)", "[_]"]


def test_extract_native_document_input_ignores_filled_and_line_shapes(
    tmp_path: Path,
) -> None:
    pdf_path = tmp_path / "markers.pdf"
    _create_marker_pdf(str(pdf_path))

    result = extract_native_document_input(pdf_path)

    marker_tokens = [t for t in result.pages[0].tokens if t.text in ("[_]", "(_)")]
    assert len(marker_tokens) == 2


def test_extract_ocr_document_input_skips_empty_words() -> None:
    ocr_result = OCRResult(language="en")
    ocr_page = OCRPage(
        page_number=1,
        width=100,
        height=100,
        text="",
        average_confidence=0.0,
        lines=[
            {
                "text": "",
                "confidence": 0.0,
                "boundingBox": {"x": 0, "y": 0, "width": 0, "height": 0},
                "words": [
                    {
                        "text": "   ",
                        "confidence": 10.0,
                        "boundingBox": {"x": 0, "y": 0, "width": 1, "height": 1},
                    }
                ],
            }
        ],
    )
    ocr_result.pages = [ocr_page]

    result = extract_ocr_document_input(ocr_result)

    assert result.pages[0].tokens == ()
