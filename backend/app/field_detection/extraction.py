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
                if (
                    raw_type == "Button"
                    or widget.field_type == fitz.PDF_WIDGET_TYPE_BUTTON
                ):
                    # Pushbuttons (e.g. "Drucken", "Alle Angaben löschen" on
                    # German municipal forms) are UI action buttons, never
                    # data-entry fields to ask the user about.
                    continue
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


def _is_empty_box_border_hallucination(
    text: str,
    confidence: float,
    box: dict[str, Any],
    page_width: float,
) -> bool:
    """Detects single-word OCR hallucinations produced when Tesseract tries to
    read the wide horizontal border of an empty drawn input box as 1–2 chars
    (e.g. `"PT"` at conf 15, `"|"` at conf 47, `"اا"` at conf 52 spanning 80%
    of the page width)."""
    if page_width <= 0:
        return False
    width = float(box.get("width", 0.0))
    height = float(box.get("height", 0.0))
    if width < page_width * 0.5:
        return False
    char_count = max(len(text), 1)
    avg_char_width = width / char_count
    if confidence < 30.0:
        return True
    return avg_char_width >= max(height * 2.5, 120.0)


def _normalize_ocr_line_words(
    raw_words: list[dict[str, Any]],
) -> list[tuple[str, dict[str, Any]]]:
    """Pairs non-empty OCR words with their dicts and recovers a trailing
    asterisk that Tesseract misread as an unpaired straight quote (`Nachname ":`
    -> `Nachname *:`). Paired quotes (`Hinweis "Abschnitt A":`) and attached
    unit quotes (`5":`) are never modified."""
    cleaned: list[tuple[str, dict[str, Any]]] = []
    for word in raw_words:
        text = (word.get("text") or "").strip()
        if text:
            cleaned.append((text, word))

    if len(cleaned) >= 2:
        total_quotes = sum(t.count('"') for t, _ in cleaned)
        last_text, last_word = cleaned[-1]
        prev_text, _ = cleaned[-2]
        if (
            total_quotes == 1
            and last_text in ('"', '":', '"：')
            and (prev_text[-1].isalpha() or prev_text.endswith(")"))
        ):
            cleaned[-1] = (last_text.replace('"', "*"), last_word)

    return cleaned


def _extract_raster_ruled_regions(
    page: fitz.Page,
    page_number: int,
    target_width: int,
    target_height: int,
    tokens: list[DetectionToken],
) -> tuple[RuledRegion, ...]:
    """Detects drawn input boxes and horizontal underlines on raster/scanned PDF
    pages using local background subtraction in Pillow, returning regions in the
    OCR page's `(target_width, target_height)` pixel coordinate space."""
    if target_width <= 0 or target_height <= 0:
        return ()

    from PIL import Image, ImageChops, ImageFilter

    pix = page.get_pixmap(dpi=150, colorspace=fitz.csGRAY, alpha=False)
    w, h = pix.width, pix.height
    if w <= 0 or h <= 0:
        return ()

    gray = Image.frombytes("L", (w, h), pix.samples)
    blurred = gray.filter(ImageFilter.BoxBlur(15))
    diff = ImageChops.subtract(blurred, gray)
    binary = diff.point(lambda v: 255 if v >= 10 else 0)

    # Mask out confirmed OCR word regions so dense letter strokes never bridge
    # into synthetic underlines or boxes.
    inv_sx = w / float(target_width)
    inv_sy = h / float(target_height)
    for token in tokens:
        if token.confidence < 0.55:
            continue
        tb = token.bounding_box
        x0 = max(0, int(tb.x * inv_sx) - 1)
        y0 = max(0, int(tb.y * inv_sy) - 1)
        x1 = min(w, int((tb.x + tb.width) * inv_sx) + 1)
        y1 = min(h, int((tb.y + tb.height) * inv_sy) + 1)
        if x1 > x0 and y1 > y0:
            binary.paste(0, (x0, y0, x1, y1))

    thick = binary.filter(ImageFilter.MaxFilter(3))
    h_mask = thick.filter(ImageFilter.BoxBlur((25, 0))).point(
        lambda v: 255 if v >= 200 else 0
    )

    raw = h_mask.tobytes()
    min_seg_w = max(int(w * 0.08), 50)
    zero_row = b"\x00" * w
    row_segs: list[tuple[int, int, int]] = []

    for y in range(h):
        row = raw[y * w : (y + 1) * w]
        if row == zero_row:
            continue
        pos = 0
        while pos < w:
            start = row.find(255, pos)
            if start == -1:
                break
            end = row.find(0, start)
            if end == -1:
                end = w
            if end - start >= min_seg_w:
                row_segs.append((y, start, end))
            pos = end + 1

    merged: list[dict[str, int]] = []
    for y, x0, x1 in row_segs:
        for seg in merged:
            if (
                y - seg["y1"] <= 4
                and abs(x0 - seg["x0"]) <= 15
                and abs(x1 - seg["x1"]) <= 15
            ):
                seg["y1"] = y
                seg["x0"] = min(seg["x0"], x0)
                seg["x1"] = max(seg["x1"], x1)
                break
        else:
            merged.append({"y0": y, "y1": y, "x0": x0, "x1": x1})

    thick_raw = thick.tobytes()
    used: set[int] = set()
    regions: list[RuledRegion] = []
    sx = float(target_width) / float(w)
    sy = float(target_height) / float(h)

    for i, top in enumerate(merged):
        if i in used:
            continue
        ty = (top["y0"] + top["y1"]) // 2
        best_box: tuple[int, int, int, int, int] | None = None
        for j in range(i + 1, len(merged)):
            if j in used:
                continue
            bot = merged[j]
            by = (bot["y0"] + bot["y1"]) // 2
            dy = by - ty
            if dy < 12:
                continue
            if dy > int(h * 0.25):
                break
            if abs(top["x0"] - bot["x0"]) <= 20 and abs(top["x1"] - bot["x1"]) <= 20:
                lx = min(top["x0"], bot["x0"])
                rx = max(top["x1"], bot["x1"])
                while lx > 0 and any(
                    thick_raw[ty * w + max(0, lx - 1) : ty * w + lx + 2]
                ):
                    lx -= 1
                while rx < w - 1 and any(
                    thick_raw[ty * w + rx - 1 : ty * w + min(w, rx + 2)]
                ):
                    rx += 1
                left_hits = sum(
                    1
                    for yy in range(ty, by + 1)
                    if any(thick_raw[yy * w + max(0, lx - 4) : yy * w + min(w, lx + 5)])
                )
                right_hits = sum(
                    1
                    for yy in range(ty, by + 1)
                    if any(thick_raw[yy * w + max(0, rx - 4) : yy * w + min(w, rx + 5)])
                )
                if left_hits >= dy * 0.6 and right_hits >= dy * 0.6:
                    best_box = (j, lx, ty, rx - lx, by - ty)
                    break

        if best_box is not None:
            j, bx, by0, bw, bh = best_box
            used.add(i)
            used.add(j)
            regions.append(
                RuledRegion(
                    kind="box",
                    page_number=page_number,
                    bounding_box=BoundingBox(
                        x=bx * sx,
                        y=by0 * sy,
                        width=bw * sx,
                        height=bh * sy,
                    ),
                )
            )
        else:
            seg_h = top["y1"] - top["y0"] + 1
            if seg_h <= 6:
                lx, rx = top["x0"], top["x1"]
                while lx > 0 and thick_raw[ty * w + lx - 1]:
                    lx -= 1
                while rx < w - 1 and thick_raw[ty * w + rx + 1]:
                    rx += 1
                regions.append(
                    RuledRegion(
                        kind="underline",
                        page_number=page_number,
                        bounding_box=BoundingBox(
                            x=lx * sx,
                            y=ty * sy,
                            width=(rx - lx) * sx,
                            height=max(1.0, seg_h * sy),
                        ),
                    )
                )

    return tuple(regions)


def extract_ocr_document_input(
    ocr_result: OCRResult, source_pdf_path: Path | None = None
) -> DetectionDocumentInput:
    """Builds a DetectionDocumentInput from an already-completed Phase 10
    OCRResult. Coordinates stay in the rendered-image pixel space OCR
    produced (see ADR 0009) — no AcroForm widgets exist for a scanned page.

    When `source_pdf_path` is available on disk, drawn raster boxes and
    underlines are also extracted in OCR pixel space so `detect_visual_fields`
    associates scanned/camera form inputs with their labels just like native
    flattened PDFs.
    """
    pages: list[DetectionPageInput] = []
    fitz_doc: fitz.Document | None = None
    if source_pdf_path is not None and source_pdf_path.exists():
        try:
            fitz_doc = fitz.open(source_pdf_path)
        except Exception:
            fitz_doc = None

    try:
        for ocr_page in ocr_result.pages:
            tokens: list[DetectionToken] = []
            for line in ocr_page.lines:
                normalized_words = _normalize_ocr_line_words(line.get("words", []))
                for text, word in normalized_words:
                    raw_conf = float(word["confidence"])
                    box = word["boundingBox"]
                    if _is_empty_box_border_hallucination(
                        text, raw_conf, box, float(ocr_page.width)
                    ):
                        continue
                    tokens.append(
                        DetectionToken(
                            text=text,
                            confidence=max(0.0, min(1.0, raw_conf / 100.0)),
                            bounding_box=BoundingBox(
                                x=box["x"],
                                y=box["y"],
                                width=box["width"],
                                height=box["height"],
                            ),
                            source="ocr",
                        )
                    )

            ruled_regions: tuple[RuledRegion, ...] = ()
            if fitz_doc is not None:
                page_idx = ocr_page.page_number - 1
                if 0 <= page_idx < fitz_doc.page_count:
                    try:
                        ruled_regions = _extract_raster_ruled_regions(
                            fitz_doc.load_page(page_idx),
                            ocr_page.page_number,
                            ocr_page.width,
                            ocr_page.height,
                            tokens,
                        )
                    except Exception:
                        ruled_regions = ()

            pages.append(
                DetectionPageInput(
                    page_number=ocr_page.page_number,
                    width=ocr_page.width,
                    height=ocr_page.height,
                    rotation=0,
                    tokens=tuple(tokens),
                    ruled_regions=ruled_regions,
                )
            )
    finally:
        if fitz_doc is not None:
            fitz_doc.close()

    return DetectionDocumentInput(
        page_count=len(pages),
        pages=tuple(pages),
        acroform_widgets=(),
        language=ocr_result.language,
        source_pdf_path=source_pdf_path,
    )
