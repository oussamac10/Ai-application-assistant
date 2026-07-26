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

import fitz

from app.field_detection.errors import FieldDetectionProviderUnavailableError
from app.field_detection.providers.base import (
    AcroFormWidgetInput,
    BoundingBox,
    DetectionDocumentInput,
    DetectionPageInput,
    DetectionToken,
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

            pages.append(
                DetectionPageInput(
                    page_number=page_number,
                    width=page.rect.width,
                    height=page.rect.height,
                    rotation=page.rotation,
                    tokens=tuple(tokens),
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
                    )
                )

        return DetectionDocumentInput(
            page_count=doc.page_count,
            pages=tuple(pages),
            acroform_widgets=tuple(widgets),
        )
    except Exception as e:
        raise FieldDetectionProviderUnavailableError(
            "Unable to extract native document content."
        ) from e
    finally:
        doc.close()


def extract_ocr_document_input(ocr_result: OCRResult) -> DetectionDocumentInput:
    """Builds a DetectionDocumentInput from an already-completed Phase 10
    OCRResult. Coordinates stay in the rendered-image pixel space OCR
    produced (see ADR 0009) — no AcroForm widgets exist for a scanned page.
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
    )
