"""Collects native-text, AcroForm, and OCR evidence into the provider-
independent `DetectionDocumentInput` shape.

A document is routed to exactly one path by Phase 9/10 eligibility (see
service.py): an unmatched *digital* PDF uses `extract_native_document_input`
(native text + AcroForm widgets, PDF point space), an unmatched *scanned*
PDF uses `extract_ocr_document_input` (Phase 10 OCR output, rendered-image
pixel space, see ADR 0009). The two coordinate spaces are never mixed under
one DetectionPageInput.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import fitz

from app.field_detection.errors import FieldDetectionProviderUnavailableError
from app.field_detection.providers.base import (
    AcroFormWidgetInput,
    BoundingBox,
    DetectionDocumentInput,
    DetectionPageInput,
    DetectionToken,
    RuledRegion,
)
from app.ocr.models import OCRResult

# PDF field-flag bit for "Required" (PDF spec Table 221, bit position 2).
_PDF_FIELD_IS_REQUIRED = fitz.PDF_FIELD_IS_REQUIRED

_ACROFORM_TYPE_MAP = {
    "Text": "text",
    "CheckBox": "checkbox",
    "RadioButton": "radio",
    "ComboBox": "choice",
    "ListBox": "choice",
    "Signature": "signature",
}

# Many forms draw checkbox/radio controls as vector shapes rather than
# AcroForm widgets or text glyphs — an unfilled (stroked, not filled) small
# near-square shape. A circular outline (built from Bezier curves, "c" path
# items) reads as a radio control; a rectilinear outline ("re"/"l" items)
# reads as a checkbox. These are synthesized into ordinary text-like tokens
# ("[_]" / "(_)") so the rest of the pipeline's marker_type() detection
# (classification.py) treats them exactly like a text-drawn marker glyph —
# no downstream code needs to know whether a marker came from text or
# vector graphics.
_MARKER_MIN_SIZE = 4.0
_MARKER_MAX_SIZE = 24.0
_MARKER_SQUARENESS_TOLERANCE = 0.35

_CHECKBOX_GLYPH = "[_]"
_RADIO_GLYPH = "(_)"


def _marker_glyph_for_drawing(drawing: dict[str, Any]) -> str | None:
    if drawing.get("type") != "s":
        return None

    rect = drawing.get("rect")
    if rect is None:
        return None

    width, height = rect.width, rect.height
    if not (_MARKER_MIN_SIZE <= width <= _MARKER_MAX_SIZE):
        return None
    if not (_MARKER_MIN_SIZE <= height <= _MARKER_MAX_SIZE):
        return None
    if abs(width - height) > _MARKER_SQUARENESS_TOLERANCE * max(width, height):
        return None

    item_commands = {item[0] for item in drawing.get("items", [])}
    if not item_commands:
        return None
    if item_commands == {"c"}:
        return _RADIO_GLYPH
    if item_commands <= {"re", "l"}:
        return _CHECKBOX_GLYPH
    return None


# A drawn region is only an input area within these bounds. Narrower than this
# is a tick or a bullet; taller than a page is a border. Deliberately generous
# — filtering happens later on evidence, not here on size alone.
_MIN_REGION_WIDTH = 40.0
_MAX_UNDERLINE_HEIGHT = 3.0
_MIN_BOX_HEIGHT = 8.0
_MAX_BOX_HEIGHT = 200.0


def _extract_ruled_regions(
    page: fitz.Page, page_number: int
) -> tuple[RuledRegion, ...]:
    """Drawn underlines and boxes, which is where a flattened form says
    "write here"."""
    regions: list[RuledRegion] = []
    for drawing in page.get_drawings():
        rect = drawing.get("rect")
        if rect is None or rect.width < _MIN_REGION_WIDTH:
            continue
        if rect.height <= _MAX_UNDERLINE_HEIGHT:
            kind = "underline"
        elif _MIN_BOX_HEIGHT <= rect.height <= _MAX_BOX_HEIGHT:
            kind = "box"
        else:
            continue
        regions.append(
            RuledRegion(
                kind=kind,
                page_number=page_number,
                bounding_box=BoundingBox(
                    x=rect.x0, y=rect.y0, width=rect.width, height=rect.height
                ),
            )
        )
    return tuple(regions)


def _extract_marker_tokens(page: fitz.Page) -> list[DetectionToken]:
    tokens: list[DetectionToken] = []
    for drawing in page.get_drawings():
        glyph = _marker_glyph_for_drawing(drawing)
        if glyph is None:
            continue
        rect = drawing["rect"]
        tokens.append(
            DetectionToken(
                text=glyph,
                confidence=1.0,
                bounding_box=BoundingBox(
                    x=rect.x0, y=rect.y0, width=rect.width, height=rect.height
                ),
                source="native",
            )
        )
    return tokens


def _widget_on_state(widget: Any) -> str | None:
    """The value a checkbox writes when ticked, or None.

    PyMuPDF raises for widget types that have no on-state, so this is guarded
    rather than branched on type — a new widget kind must not break extraction.
    """
    try:
        return widget.on_state() or None
    except Exception:
        return None


def _widget_parent_name(widget: Any) -> str | None:
    """The widget's parent field name, when it is a kid of a shared field.

    A native radio group is expressed this way. Most real forms do not use it
    — every checkbox on the Stuttgart application is an independent field —
    so grouping cannot depend on it, but it is decisive when present.
    """
    try:
        parent = getattr(widget, "parent", None)
        name = getattr(parent, "field_name", None) if parent is not None else None
        return str(name) if name else None
    except Exception:
        return None


def extract_native_document_input(pdf_path: Path) -> DetectionDocumentInput:
    """Extracts native text tokens and AcroForm widgets via PyMuPDF.

    Coordinates are in PDF point space, already adjusted for each page's own
    rotation (PyMuPDF applies the /Rotate transform to both `get_text` and
    widget rects, matching what a viewer renders).
    """
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        raise FieldDetectionProviderUnavailableError(
            "Unable to open document for native extraction."
        ) from e

    try:
        pages: list[DetectionPageInput] = []
        widgets: list[AcroFormWidgetInput] = []

        for index in range(doc.page_count):
            page = doc.load_page(index)
            page_number = index + 1

            tokens: list[DetectionToken] = []
            for x0, y0, x1, y1, text, *_rest in page.get_text("words"):
                cleaned = text.strip()
                if not cleaned:
                    continue
                tokens.append(
                    DetectionToken(
                        text=cleaned,
                        confidence=1.0,
                        bounding_box=BoundingBox(
                            x=x0, y=y0, width=x1 - x0, height=y1 - y0
                        ),
                        source="native",
                    )
                )

            tokens.extend(_extract_marker_tokens(page))

            pages.append(
                DetectionPageInput(
                    page_number=page_number,
                    width=page.rect.width,
                    height=page.rect.height,
                    rotation=page.rotation,
                    tokens=tuple(tokens),
                    ruled_regions=_extract_ruled_regions(page, page_number),
                )
            )

            for widget in page.widgets() or []:
                raw_type = widget.field_type_string or ""
                mapped_type = _ACROFORM_TYPE_MAP.get(raw_type, "text")
                required = bool((widget.field_flags or 0) & _PDF_FIELD_IS_REQUIRED)
                rect = widget.rect
                widgets.append(
                    AcroFormWidgetInput(
                        field_name=widget.field_name or "",
                        field_type=mapped_type,
                        rect=BoundingBox(
                            x=rect.x0,
                            y=rect.y0,
                            width=rect.width,
                            height=rect.height,
                        ),
                        page_number=page_number,
                        required=required,
                        field_label=(widget.field_label or None),
                        export_value=_widget_on_state(widget),
                        parent_name=_widget_parent_name(widget),
                    )
                )

        return DetectionDocumentInput(
            page_count=doc.page_count,
            pages=tuple(pages),
            acroform_widgets=tuple(widgets),
            source_pdf_path=pdf_path,
        )
    except Exception as e:
        raise FieldDetectionProviderUnavailableError(
            "Unable to extract native document content."
        ) from e
    finally:
        doc.close()


def extract_ocr_document_input(
    ocr_result: OCRResult, source_pdf_path: Path | None = None
) -> DetectionDocumentInput:
    """Builds a DetectionDocumentInput from an already-completed Phase 10
    OCRResult. Coordinates stay in the rendered-image pixel space OCR
    produced (see ADR 0009) — no AcroForm widgets exist for a scanned page.

    `source_pdf_path` is passed through unchanged for providers that must
    upload the original file (Azure); it plays no part in OCR extraction.
    """
    pages: list[DetectionPageInput] = []

    for ocr_page in ocr_result.pages:
        tokens: list[DetectionToken] = []
        for line in ocr_page.lines:
            for word in line.get("words", []):
                text = (word.get("text") or "").strip()
                if not text:
                    continue
                box = word["boundingBox"]
                tokens.append(
                    DetectionToken(
                        text=text,
                        confidence=max(
                            0.0, min(1.0, float(word["confidence"]) / 100.0)
                        ),
                        bounding_box=BoundingBox(
                            x=box["x"],
                            y=box["y"],
                            width=box["width"],
                            height=box["height"],
                        ),
                        source="ocr",
                    )
                )

        pages.append(
            DetectionPageInput(
                page_number=ocr_page.page_number,
                width=ocr_page.width,
                height=ocr_page.height,
                rotation=0,
                tokens=tuple(tokens),
            )
        )

    return DetectionDocumentInput(
        page_count=len(pages),
        pages=tuple(pages),
        acroform_widgets=(),
        language=ocr_result.language,
        source_pdf_path=source_pdf_path,
    )
