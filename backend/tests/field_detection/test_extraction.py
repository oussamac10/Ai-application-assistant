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


def test_extract_ocr_document_input_recovers_corrupted_asterisk_and_extracts_raster_boxes(
    tmp_path: Path,
) -> None:
    import fitz
    from PIL import Image, ImageDraw

    from app.field_detection.providers.local import LocalFieldDetectionProvider
    from app.field_detection.question_bridge import _resolve_requiredness

    # Build a 300-DPI synthetic scanned form PNG (2480 x 3509) with 5 drawn boxes
    # and wrap it into an A4 PDF (595 x 842 pt) just like S1-02 image normalization.
    img = Image.new("RGB", (2480, 3509), "white")
    draw = ImageDraw.Draw(img)
    box_ys = [574, 804, 1032, 1262, 1492]
    for by in box_ys:
        draw.rectangle([224, by, 2232, by + 102], outline=(90, 90, 90), width=4)

    png_path = tmp_path / "scan.png"
    img.save(png_path, format="PNG")

    pdf_path = tmp_path / "scan.pdf"
    pdf_doc = fitz.open()
    pdf_page = pdf_doc.new_page(width=595, height=842)
    pdf_page.insert_image(pdf_page.rect, filename=str(png_path))
    pdf_doc.save(str(pdf_path))
    pdf_doc.close()

    # Simulate Tesseract OCR output including:
    # - `Nachname ":` (asterisk before colon misread as unpaired quote `"`)
    # - `PT` (conf 16) and `|` (conf 47) 2004px-wide empty-box border hallucinations
    # - A legitimate paired-quote label `Hinweis "Abschnitt A":` that must keep its quotes
    ocr_result = OCRResult(language="auto")
    ocr_page = OCRPage(
        page_number=1,
        width=2480,
        height=3509,
        text='Vorname *:\nNachname ":\nPT\nGeburtsdatum (TT.MM.JJJJ) *:\nAktuelle Anschrift (StraBe, Nr., PLZ, Ort) *:\nHinweis "Abschnitt A":\n|',
        average_confidence=78.0,
        lines=[
            {
                "text": "Vorname *:",
                "confidence": 90.0,
                "boundingBox": {"x": 231, "y": 508, "width": 225, "height": 35},
                "words": [
                    {
                        "text": "Vorname",
                        "confidence": 91.0,
                        "boundingBox": {"x": 231, "y": 508, "width": 183, "height": 35},
                    },
                    {
                        "text": "*:",
                        "confidence": 87.0,
                        "boundingBox": {"x": 429, "y": 508, "width": 27, "height": 34},
                    },
                ],
            },
            {
                "text": 'Nachname ":',
                "confidence": 92.5,
                "boundingBox": {"x": 233, "y": 737, "width": 259, "height": 36},
                "words": [
                    {
                        "text": "Nachname",
                        "confidence": 93.0,
                        "boundingBox": {"x": 233, "y": 737, "width": 216, "height": 36},
                    },
                    {
                        "text": '":',
                        "confidence": 92.0,
                        "boundingBox": {"x": 465, "y": 738, "width": 27, "height": 33},
                    },
                ],
            },
            {
                "text": "PT",
                "confidence": 16.0,
                "boundingBox": {"x": 228, "y": 803, "width": 2003, "height": 103},
                "words": [
                    {
                        "text": "PT",
                        "confidence": 16.0,
                        "boundingBox": {
                            "x": 228,
                            "y": 803,
                            "width": 2003,
                            "height": 103,
                        },
                    }
                ],
            },
            {
                "text": "Geburtsdatum (TT.MM.JJJJ) *:",
                "confidence": 91.0,
                "boundingBox": {"x": 231, "y": 966, "width": 623, "height": 45},
                "words": [
                    {
                        "text": "Geburtsdatum",
                        "confidence": 93.0,
                        "boundingBox": {"x": 231, "y": 966, "width": 286, "height": 36},
                    },
                    {
                        "text": "(TT.MM.JJJJ)",
                        "confidence": 88.0,
                        "boundingBox": {"x": 536, "y": 967, "width": 273, "height": 44},
                    },
                    {
                        "text": "*:",
                        "confidence": 92.0,
                        "boundingBox": {"x": 827, "y": 967, "width": 27, "height": 34},
                    },
                ],
            },
            {
                "text": "Aktuelle Anschrift (StraBe, Nr., PLZ, Ort) *:",
                "confidence": 92.0,
                "boundingBox": {"x": 231, "y": 1194, "width": 860, "height": 45},
                "words": [
                    {
                        "text": "Aktuelle",
                        "confidence": 93.0,
                        "boundingBox": {
                            "x": 231,
                            "y": 1195,
                            "width": 159,
                            "height": 35,
                        },
                    },
                    {
                        "text": "Anschrift",
                        "confidence": 91.0,
                        "boundingBox": {
                            "x": 406,
                            "y": 1195,
                            "width": 177,
                            "height": 35,
                        },
                    },
                    {
                        "text": "(StraBe,",
                        "confidence": 92.0,
                        "boundingBox": {
                            "x": 600,
                            "y": 1194,
                            "width": 158,
                            "height": 45,
                        },
                    },
                    {
                        "text": "Nr.,",
                        "confidence": 91.0,
                        "boundingBox": {
                            "x": 777,
                            "y": 1195,
                            "width": 68,
                            "height": 40,
                        },
                    },
                    {
                        "text": "PLZ,",
                        "confidence": 96.0,
                        "boundingBox": {
                            "x": 865,
                            "y": 1195,
                            "width": 89,
                            "height": 40,
                        },
                    },
                    {
                        "text": "Ort)",
                        "confidence": 93.0,
                        "boundingBox": {
                            "x": 972,
                            "y": 1194,
                            "width": 74,
                            "height": 45,
                        },
                    },
                    {
                        "text": "*:",
                        "confidence": 93.0,
                        "boundingBox": {
                            "x": 1064,
                            "y": 1195,
                            "width": 27,
                            "height": 34,
                        },
                    },
                ],
            },
            {
                "text": 'Hinweis "Abschnitt A":',
                "confidence": 94.0,
                "boundingBox": {"x": 233, "y": 1424, "width": 480, "height": 36},
                "words": [
                    {
                        "text": "Hinweis",
                        "confidence": 94.0,
                        "boundingBox": {
                            "x": 233,
                            "y": 1424,
                            "width": 160,
                            "height": 36,
                        },
                    },
                    {
                        "text": '"Abschnitt',
                        "confidence": 94.0,
                        "boundingBox": {
                            "x": 405,
                            "y": 1424,
                            "width": 200,
                            "height": 36,
                        },
                    },
                    {
                        "text": 'A":',
                        "confidence": 94.0,
                        "boundingBox": {
                            "x": 615,
                            "y": 1424,
                            "width": 98,
                            "height": 36,
                        },
                    },
                ],
            },
            {
                "text": "|",
                "confidence": 47.0,
                "boundingBox": {"x": 227, "y": 1491, "width": 2004, "height": 104},
                "words": [
                    {
                        "text": "|",
                        "confidence": 47.0,
                        "boundingBox": {
                            "x": 227,
                            "y": 1491,
                            "width": 2004,
                            "height": 104,
                        },
                    }
                ],
            },
        ],
    )
    ocr_result.pages = [ocr_page]

    doc_input = extract_ocr_document_input(ocr_result, source_pdf_path=pdf_path)
    page = doc_input.pages[0]

    token_texts = [t.text for t in page.tokens]
    assert "PT" not in token_texts
    assert "|" not in token_texts
    assert 'A":' in token_texts  # Paired quotes stay untouched

    box_regions = [r for r in page.ruled_regions if r.kind == "box"]
    assert len(box_regions) == 5

    detected = LocalFieldDetectionProvider().detect(doc_input)
    by_name = {c.normalized_name: c for c in detected.fields}
    assert "nachname" in by_name
    assert "aktuelle_anschrift_strabe_nr_plz_ort" in by_name
    for c in detected.fields:
        assert c.input_bounding_box is not None
        assert c.input_bounding_box.width > 1800
        assert c.field_type != "multiline_text"
        assert c.source == "ocr"

    assert '"' not in by_name["nachname"].label

    from typing import Any

    class _StubField:
        def __init__(self, candidate: Any) -> None:
            self.label = candidate.label
            self.required = candidate.required

    assert _resolve_requiredness(_StubField(by_name["nachname"])) == "required"
    assert (
        _resolve_requiredness(_StubField(by_name["hinweis_abschnitt_a"])) == "unknown"
    )
