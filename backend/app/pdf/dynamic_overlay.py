"""Dynamic coordinate-overlay PDF rendering for uploaded documents (Phase 17).

When a user uploads an arbitrary PDF form, field detection (`app/field_detection`)
identifies candidate fields along with their page number and `input_bounding_box`.
Once the user completes the guided Q&A session and confirms their answers, this
module maps each `FormField` in the dynamic `FormVersion` back to its originating
`DetectedField` and overlays the confirmed `output_value` (and any vector
signatures) onto a copy of the uploaded PDF using PyMuPDF (`fitz`).

Invariants (per `docs/claude/domain-rules.md` and ADR 0010):
- Never guess coordinates: only fields carrying an explicit `input_bounding_box`
  from field detection are drawn onto the page.
- Never fall back to `settings.PDF_TEMPLATE_KEY` or an unrelated template.
- A dynamic session without a backing `SourceDocument` and mappable detected
  coordinates is rejected with `dynamic_pdf_export_not_supported`.
"""

from __future__ import annotations

import logging
import re
import shutil
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

import app.auth.models  # noqa: F401
from app.answers.models import FormAnswer
from app.answers.signatures import PENDING_MANUAL_SIGNATURE
from app.documents.models import SourceDocument
from app.field_detection.classification import (
    is_blank_run,
    marker_type,
    starts_with_blank_run,
)
from app.field_detection.extraction import extract_native_document_input
from app.field_detection.models import DetectedField, FieldDetectionResult
from app.forms.models import FormField, FormVersion
from app.ocr.models import OCRResult
from app.pdf.formatting import format_field_value
from app.pdf.renderers.pypdf_renderer import PDFRenderResult
from app.pdf.signature_render import (
    SIGNATURE_EXPORT_FAILED,
    SIGNATURE_MAPPING_MISSING,
    SignatureBox,
    SignatureRenderError,
    render_signature,
)
from app.sessions.models import FormSession

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FieldLocationInfo:
    """Page and bounding-box location of a dynamically detected form field."""

    page_number: int
    input_bounding_box: dict[str, float] | None
    label_bounding_box: dict[str, float] | None
    source: str


def _sanitize_key(name: str) -> str:
    """Matches `app/field_detection/question_bridge.py:_unique_key` base key."""
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", name.strip().lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned or not cleaned[0].isalpha():
        cleaned = f"field_{cleaned}" if cleaned else "field"
    return cleaned


def _preview_unique_key(base_name: str, used: set[str]) -> str:
    """Computes the next unique key without mutating `used`."""
    base = _sanitize_key(base_name)
    candidate = base
    counter = 2
    while candidate in used:
        suffix = f"_{counter}"
        candidate = f"{base}{suffix}"
        counter += 1
    return candidate


def get_latest_completed_detection(
    db: Session, source_document_id: str
) -> FieldDetectionResult | None:
    """Returns the most recent completed FieldDetectionResult for a document."""
    stmt = (
        select(FieldDetectionResult)
        .where(
            FieldDetectionResult.source_document_id == source_document_id,
            FieldDetectionResult.status == "completed",
        )
        .order_by(
            FieldDetectionResult.analysis_version.desc(),
            FieldDetectionResult.created_at.desc(),
        )
    )
    return db.scalars(stmt).first()


def map_form_fields_to_detected_fields(
    version_fields: list[FormField],
    detected_fields: list[DetectedField],
) -> dict[str, DetectedField]:
    """Maps each `FormField.key` in `version_fields` to its originating `DetectedField`.

    `create_session_from_confirmed_fields` iterates non-rejected `DetectedField`
    rows in `display_order` and assigns keys via `_unique_key(df.normalized_name)`.
    Walking `version_fields` in `position` order and advancing a cursor over the
    candidate `DetectedField` list reconstructs the exact 1-to-1 pairing without
    requiring extra foreign-key columns on `form_fields`.
    """
    candidates = [
        df
        for df in sorted(detected_fields, key=lambda f: f.display_order)
        if df.review_status != "rejected"
    ]
    ordered_form_fields = sorted(version_fields, key=lambda f: f.position)

    matched: dict[str, DetectedField] = {}
    used_keys: set[str] = set()
    cursor = 0

    for form_field in ordered_form_fields:
        found_idx: int | None = None
        for idx in range(cursor, len(candidates)):
            expected_key = _preview_unique_key(
                candidates[idx].normalized_name, used_keys
            )
            if expected_key == form_field.key:
                found_idx = idx
                break

        if found_idx is not None:
            used_keys.add(form_field.key)
            matched[form_field.key] = candidates[found_idx]
            cursor = found_idx + 1
        else:
            # Fallback: match any remaining candidate whose sanitized base name
            # equals the form field key prefix.
            for idx in range(cursor, len(candidates)):
                base = _sanitize_key(candidates[idx].normalized_name)
                if form_field.key == base or form_field.key.startswith(f"{base}_"):
                    used_keys.add(form_field.key)
                    matched[form_field.key] = candidates[idx]
                    cursor = idx + 1
                    break

    return matched


def get_field_location_for_session(
    db: Session,
    session: FormSession,
    field: FormField,
) -> tuple[FieldLocationInfo | None, SourceDocument | None]:
    """Looks up the document and bounding-box metadata for a single field in a session."""
    if not session.source_document_id:
        return None, None

    source_doc = db.get(SourceDocument, session.source_document_id)
    if not source_doc:
        return None, None

    detection = get_latest_completed_detection(db, source_doc.id)
    if not detection or not detection.fields:
        return None, source_doc

    version = session.version or db.get(FormVersion, session.form_version_id)
    if not version or not version.fields:
        return None, source_doc

    mapping = map_form_fields_to_detected_fields(
        list(version.fields), list(detection.fields)
    )
    detected = mapping.get(field.key)
    if not detected:
        return None, source_doc

    def _clean_box(raw: dict[str, Any] | None) -> dict[str, float] | None:
        if not raw:
            return None
        try:
            return {
                "x": float(raw["x"]),
                "y": float(raw["y"]),
                "width": float(raw["width"]),
                "height": float(raw["height"]),
            }
        except (KeyError, TypeError, ValueError):
            return None

    return (
        FieldLocationInfo(
            page_number=detected.page_number,
            input_bounding_box=_clean_box(detected.input_bounding_box),
            label_bounding_box=_clean_box(detected.label_bounding_box),
            source=detected.source,
        ),
        source_doc,
    )


def has_exportable_dynamic_document(db: Session, session: FormSession) -> bool:
    """Returns True when `session` is linked to a SourceDocument on disk that has
    at least one confirmed/usable detected field with an `input_bounding_box`.
    """
    if not session.source_document_id:
        return False

    source_doc = db.get(SourceDocument, session.source_document_id)
    if not source_doc or not source_doc.storage_path:
        return False

    if not Path(source_doc.storage_path).is_file():
        return False

    detection = get_latest_completed_detection(db, source_doc.id)
    if not detection or not detection.fields:
        return False

    return any(
        df.review_status != "rejected" and bool(df.input_bounding_box)
        for df in detection.fields
    )


def _load_ocr_page_dimensions(
    db: Session, source_document_id: str
) -> dict[int, tuple[float, float]]:
    """Returns `{page_number: (width_px, height_px)}` from OCRPage rows if present."""
    stmt = select(OCRResult).where(
        OCRResult.source_document_id == source_document_id,
        OCRResult.status == "completed",
    )
    ocr_result = db.scalars(stmt).first()
    if not ocr_result or not ocr_result.pages:
        return {}

    dims: dict[int, tuple[float, float]] = {}
    for page in ocr_result.pages:
        if page.width > 0 and page.height > 0:
            dims[page.page_number] = (float(page.width), float(page.height))
    return dims


def _resolve_pdf_rect(
    raw_box: dict[str, Any],
    *,
    source: str,
    page_number: int,
    pdf_page_width: float,
    pdf_page_height: float,
    ocr_dims: dict[int, tuple[float, float]],
) -> tuple[float, float, float, float] | None:
    """Converts a `DetectedField.input_bounding_box` into PDF page points
    `(x, y, width, height)` with top-left origin.
    """
    try:
        x = float(raw_box["x"])
        y = float(raw_box["y"])
        width = float(raw_box["width"])
        height = float(raw_box["height"])
    except (KeyError, TypeError, ValueError):
        return None

    if width <= 0 or height < 0 or x < 0 or y < 0:
        return None

    # A drawn underline (RuledRegion with kind="underline") has height == 0 at
    # the baseline of the writing area. Place an 11.5pt single-line box directly
    # above the underline so overlaid text rests on the rule without overlapping
    # a tight label caption above it.
    if height <= 2.0:
        line_height = 11.5
        y = max(0.0, y - line_height)
        height = line_height

    if source == "ocr" and page_number in ocr_dims:
        ocr_w, ocr_h = ocr_dims[page_number]
        if ocr_w > 0 and ocr_h > 0:
            scale_x = pdf_page_width / ocr_w
            scale_y = pdf_page_height / ocr_h
            x *= scale_x
            width *= scale_x
            y *= scale_y
            height *= scale_y

    return x, y, width, height


def _resolve_effective_input_box(
    detected: DetectedField,
    form_field_type: str,
    native_page_tokens: Sequence[Any],
) -> dict[str, Any] | None:
    """Resolves the effective `input_bounding_box` for `detected`.

    Handles:
    1. Explicit `detected.input_bounding_box`, including legacy inline-blank
       fields where `input_bounding_box` stored `after.bounding_box` instead
       of the blank gap between `label_bounding_box` (`before`) and `after`.
    2. Blank-run fields where `input_bounding_box` was `None` in an earlier
       detection pass, by locating the blank-run token (`…………` or `________`)
       on the same physical line in `native_page_tokens`.
    3. Choice/boolean fields falling back to `label_bounding_box`.
    """
    raw_input = detected.input_bounding_box
    raw_label = detected.label_bounding_box

    if raw_input and raw_label:
        in_coords = _extract_token_box_coords(raw_input)
        lbl_coords = _extract_token_box_coords(raw_label)
        if in_coords is not None and lbl_coords is not None:
            ix, iy, iw, ih = in_coords
            lx, ly, lw, lh = lbl_coords
            same_line = abs(iy - ly) <= max(lh, ih, 6.0)
            gap = ix - (lx + lw)
            if same_line and gap >= 12.0 and native_page_tokens:
                overlaps_printed_word = any(
                    not (
                        is_blank_run(getattr(t, "text", ""))
                        or starts_with_blank_run(getattr(t, "text", ""))
                    )
                    and (
                        tc := _extract_token_box_coords(
                            getattr(t, "bounding_box", None)
                        )
                    )
                    is not None
                    and abs(tc[0] - ix) <= 2.5
                    and abs(tc[1] - iy) <= 2.5
                    for t in native_page_tokens
                )
                if overlaps_printed_word:
                    return {
                        "x": lx + lw + 2.0,
                        "y": ly,
                        "width": max(gap - 4.0, 16.0),
                        "height": max(lh, ih),
                    }

    if raw_input:
        return raw_input

    if raw_label:
        lbl_coords = _extract_token_box_coords(raw_label)
        if lbl_coords is not None and native_page_tokens:
            lx, ly, lw, lh = lbl_coords
            blank_boxes: list[tuple[float, float, float, float]] = []
            for t in native_page_tokens:
                txt = getattr(t, "text", "")
                if not (is_blank_run(txt) or starts_with_blank_run(txt)):
                    continue
                tc = _extract_token_box_coords(getattr(t, "bounding_box", None))
                if tc is None:
                    continue
                tx, ty, tw, th = tc
                if abs(ty - ly) <= max(lh, th, 6.0) and tx >= lx:
                    blank_boxes.append((tx, ty, tw, th))
            if blank_boxes:
                min_x = min(b[0] for b in blank_boxes)
                min_y = min(b[1] for b in blank_boxes)
                max_r = max(b[0] + b[2] for b in blank_boxes)
                max_b = max(b[1] + b[3] for b in blank_boxes)
                return {
                    "x": min_x,
                    "y": min_y,
                    "width": max_r - min_x,
                    "height": max_b - min_y,
                }
        if form_field_type in ("single_choice", "multiple_choice", "boolean"):
            return raw_label

    return None


def render_dynamic_overlay_pdf(
    *,
    db: Session,
    session: FormSession,
    version: FormVersion,
    source_doc: SourceDocument,
    detection: FieldDetectionResult,
    answers_by_field_id: dict[str, FormAnswer],
    output_path: Path,
) -> PDFRenderResult:
    """Copies the uploaded `source_doc` PDF to `output_path` and overlays all
    confirmed answers at their detected `input_bounding_box` coordinates.
    """
    import fitz

    source_path = Path(source_doc.storage_path)
    if not source_path.is_file():
        raise ValueError("Uploaded source PDF file is no longer available on disk.")

    field_to_detected = map_form_fields_to_detected_fields(
        list(version.fields), list(detection.fields)
    )
    ocr_dims = _load_ocr_page_dimensions(db, source_doc.id)

    native_tokens_by_page: dict[int, tuple[Any, ...]] = {}
    try:
        native_doc = extract_native_document_input(source_path)
        for p in native_doc.pages:
            native_tokens_by_page[p.page_number] = p.tokens
    except Exception:
        native_tokens_by_page = {}

    output_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source_path, output_path)

    document = fitz.open(output_path)
    try:
        page_count = document.page_count
        for form_field in sorted(version.fields, key=lambda f: f.position):
            ans = answers_by_field_id.get(form_field.id)
            if not ans or ans.status not in ("confirmed", PENDING_MANUAL_SIGNATURE):
                continue

            detected = field_to_detected.get(form_field.key)
            raw_box = None
            if detected is not None:
                raw_box = _resolve_effective_input_box(
                    detected,
                    form_field.field_type,
                    native_tokens_by_page.get(detected.page_number, ()),
                )

            if not detected or not raw_box:
                if (
                    form_field.field_type == "signature"
                    and ans.status == "confirmed"
                    and ans.normalized_value
                ):
                    raise SignatureRenderError(
                        SIGNATURE_MAPPING_MISSING,
                        "This template has no signature area mapped.",
                    )
                continue

            page_idx = detected.page_number - 1
            if not (0 <= page_idx < page_count):
                if form_field.field_type == "signature":
                    raise SignatureRenderError(
                        SIGNATURE_EXPORT_FAILED,
                        "The signature page is outside the document.",
                    )
                continue

            page = document[page_idx]
            pdf_w = float(page.rect.width)
            pdf_h = float(page.rect.height)

            resolved = _resolve_pdf_rect(
                raw_box,
                source=detected.source,
                page_number=detected.page_number,
                pdf_page_width=pdf_w,
                pdf_page_height=pdf_h,
                ocr_dims=ocr_dims,
            )
            if resolved is None:
                continue

            x, y, width, height = resolved

            # 1. Signature fields: draw vector strokes into the detected box.
            if form_field.field_type == "signature":
                if ans.status == PENDING_MANUAL_SIGNATURE or not ans.normalized_value:
                    continue
                sig_h = max(height, 28.0)
                sig_y = max(0.0, y + height - sig_h)
                sig_box = SignatureBox(
                    page_number=detected.page_number,
                    x=x,
                    y=sig_y,
                    width=width,
                    height=sig_h,
                )
                render_signature(page, sig_box, ans.normalized_value)
                continue

            # 2. Boolean fields: draw a crisp checkmark in the checkbox square
            # only when True; leave unchecked when False (never write "Yes"/"No"
            # text over the checkbox or declaration sentence).
            if form_field.field_type == "boolean":
                raw_bool: object = ans.normalized_value
                if raw_bool is True:
                    if width <= 26 and height <= 26:
                        _draw_checkbox_mark(page, x, y, width, height)
                    else:
                        marker_rect = _find_marker_rect_in_box(
                            native_tokens_by_page.get(detected.page_number, ()),
                            box_x=x,
                            box_y=y,
                            box_w=width,
                            box_h=height,
                        )
                        if marker_rect is not None:
                            mx, my, mw, mh = marker_rect
                            _draw_checkbox_mark(page, mx, my, mw, mh)
                        else:
                            side = min(max(height, 9.0), 12.0)
                            _draw_checkbox_mark(page, x, y, side, side)
                continue

            # 2b. Choice groups backed by individual checkbox/radio squares:
            # mark the selected option square(s) directly when each option in
            # `detected.options` maps 1-to-1 to a checkbox/radio widget or
            # vector-drawn marker inside `input_bounding_box`.
            if (
                form_field.field_type in ("single_choice", "multiple_choice")
                and detected.options
                and detected.field_type in ("radio", "single_choice", "multiple_choice")
                and _try_mark_selected_choice_squares(
                    page=page,
                    detected=detected,
                    normalized_value=ans.normalized_value,
                    output_value=ans.output_value,
                    box_x=x,
                    box_y=y,
                    box_w=width,
                    box_h=height,
                    native_page_tokens=native_tokens_by_page.get(
                        detected.page_number, ()
                    ),
                )
            ):
                continue

            # 3. Standard text / choice / date / money fields.
            formatted_val = format_field_value(
                field_type=form_field.field_type,
                normalized_value=ans.normalized_value,
                output_value=ans.output_value,
                output_language=session.output_language,
            )
            formatted_val = formatted_val.strip() if formatted_val else ""
            if not formatted_val:
                continue

            page_tokens = native_tokens_by_page.get(detected.page_number, ())
            if (
                form_field.field_type == "money"
                and formatted_val.upper().endswith(" EUR")
                and page_tokens
            ):
                has_printed_euro = any(
                    getattr(t, "text", "").strip(".,;:()").lower()
                    in ("euro", "eur", "€")
                    and (
                        tc := _extract_token_box_coords(
                            getattr(t, "bounding_box", None)
                        )
                    )
                    is not None
                    and abs(tc[1] - y) <= max(height, tc[3], 6.0)
                    and x <= tc[0] <= x + width + 24.0
                    for t in page_tokens
                )
                if has_printed_euro:
                    formatted_val = formatted_val[:-4].strip()

            over_dotted_run = any(
                (
                    is_blank_run(getattr(t, "text", ""))
                    or starts_with_blank_run(getattr(t, "text", ""))
                )
                and ("." in getattr(t, "text", "") or "…" in getattr(t, "text", ""))
                and (tc := _extract_token_box_coords(getattr(t, "bounding_box", None)))
                is not None
                and abs(tc[1] - y) <= max(height, tc[3], 6.0)
                and tc[0] < x + width
                and tc[0] + tc[2] > x
                for t in page_tokens
            )

            _draw_text_in_box(
                page,
                x=x,
                y=y,
                width=width,
                height=height,
                text=formatted_val,
                multiline=(form_field.field_type == "multiline_text" or height >= 36),
                mask_dots=over_dotted_run,
            )

        # Remove interactive AcroForm widgets on the exported copy so PDF
        # viewers never cover overlaid text/checkmarks with empty interactive
        # input boxes or display form-reset/print pushbuttons.
        for page_idx in range(page_count):
            pg = document[page_idx]
            try:
                for w in list(pg.widgets() or []):
                    pg.delete_widget(w)
            except Exception:
                pass

        document.saveIncr()
    finally:
        document.close()

    file_size = output_path.stat().st_size
    return PDFRenderResult(
        page_count=page_count,
        file_size=file_size,
        output_path=output_path,
    )


def _extract_token_box_coords(
    bb: Any,
) -> tuple[float, float, float, float] | None:
    """Extracts `(x, y, width, height)` from a `BoundingBox` dataclass or `dict`."""
    if bb is None:
        return None
    try:
        if isinstance(bb, dict):
            return (
                float(bb["x"]),
                float(bb["y"]),
                float(bb["width"]),
                float(bb["height"]),
            )
        return (
            float(bb.x),
            float(bb.y),
            float(bb.width),
            float(bb.height),
        )
    except (AttributeError, KeyError, TypeError, ValueError):
        return None


def _find_marker_rect_in_box(
    native_page_tokens: Sequence[Any],
    *,
    box_x: float,
    box_y: float,
    box_w: float,
    box_h: float,
) -> tuple[float, float, float, float] | None:
    """Finds the first checkbox/radio marker token intersecting `(box_x, box_y, box_w, box_h)`."""
    import fitz

    target = fitz.Rect(
        box_x - 4.0, box_y - 4.0, box_x + box_w + 4.0, box_y + box_h + 4.0
    )
    for t in native_page_tokens:
        if marker_type(getattr(t, "text", "")) not in ("checkbox", "radio"):
            continue
        coords = _extract_token_box_coords(getattr(t, "bounding_box", None))
        if coords is None:
            continue
        tx, ty, tw, th = coords
        if fitz.Rect(tx, ty, tx + tw, ty + th).intersects(target):
            return (tx, ty, tw, th)
    return None


def _try_mark_selected_choice_squares(
    *,
    page: Any,
    detected: DetectedField,
    normalized_value: Any,
    output_value: str | None,
    box_x: float,
    box_y: float,
    box_w: float,
    box_h: float,
    native_page_tokens: Sequence[Any] = (),
) -> bool:
    """Marks the checkbox/radio widget(s) or vector marker square(s) inside
    `(box_x, box_y, box_w, box_h)` corresponding to the selected option(s) when
    a 1-to-1 mapping exists. Returns True if marks were drawn, or False to fall
    back to text rendering.
    """
    import fitz

    selected_values: set[str] = set()
    if isinstance(normalized_value, str) and normalized_value.strip():
        selected_values.add(normalized_value.strip())
    elif isinstance(normalized_value, list):
        for item in normalized_value:
            if isinstance(item, str) and item.strip():
                selected_values.add(item.strip())
    elif isinstance(normalized_value, dict):
        val = normalized_value.get("value")
        if isinstance(val, str) and val.strip():
            selected_values.add(val.strip())
    if not selected_values and output_value and output_value.strip():
        selected_values.add(output_value.strip())

    if not selected_values:
        return False

    ordered_options = sorted(detected.options, key=lambda o: o.position)
    selected_indices = [
        idx
        for idx, opt in enumerate(ordered_options)
        if opt.value.strip() in selected_values
    ]
    if not selected_indices:
        return False

    group_rect = fitz.Rect(
        box_x - 6.0, box_y - 6.0, box_x + box_w + 6.0, box_y + box_h + 6.0
    )
    choice_widget_types = {
        getattr(fitz, "PDF_WIDGET_TYPE_CHECKBOX", 2),
        getattr(fitz, "PDF_WIDGET_TYPE_RADIOBUTTON", 5),
    }
    matching_rects: list[tuple[float, float, float, float]] = []
    try:
        for w in page.widgets() or []:
            if getattr(w, "field_type", None) not in choice_widget_types:
                continue
            r = w.rect
            if r.intersects(group_rect):
                matching_rects.append(
                    (float(r.x0), float(r.y0), float(r.width), float(r.height))
                )
    except Exception:
        matching_rects = []

    matching_rects.sort(key=lambda rect: (round(rect[1] / 6.0), rect[0]))
    if len(matching_rects) != len(ordered_options) and native_page_tokens:
        token_rects: list[tuple[float, float, float, float]] = []
        for t in native_page_tokens:
            if marker_type(getattr(t, "text", "")) not in ("checkbox", "radio"):
                continue
            coords = _extract_token_box_coords(getattr(t, "bounding_box", None))
            if coords is None:
                continue
            tx, ty, tw, th = coords
            if fitz.Rect(tx, ty, tx + tw, ty + th).intersects(group_rect):
                token_rects.append((tx, ty, tw, th))
        token_rects.sort(key=lambda rect: (round(rect[1] / 6.0), rect[0]))
        if len(token_rects) == len(ordered_options):
            matching_rects = token_rects

    if len(matching_rects) != len(ordered_options):
        return False

    for idx in selected_indices:
        rx, ry, rw, rh = matching_rects[idx]
        _draw_checkbox_mark(page, rx, ry, rw, rh)
    return True


def _draw_checkbox_mark(
    page: Any, x: float, y: float, width: float, height: float
) -> None:
    """Draws a crisp vector checkmark inside a small checkbox rectangle."""
    pad_x = max(width * 0.22, 1.5)
    pad_y = max(height * 0.22, 1.5)
    p1 = (x + pad_x, y + height * 0.55)
    p2 = (x + width * 0.44, y + height - pad_y)
    p3 = (x + width - pad_x, y + pad_y)
    shape = page.new_shape()
    shape.draw_polyline([p1, p2, p3])
    shape.finish(width=1.4, color=(0.06, 0.09, 0.16), fill=None)
    shape.commit()


def _draw_text_in_box(
    page: Any,
    *,
    x: float,
    y: float,
    width: float,
    height: float,
    text: str,
    multiline: bool,
    mask_dots: bool = False,
) -> None:
    """Draws `text` inside `(x, y, width, height)` in PDF points."""
    import fitz

    rect = fitz.Rect(
        x + 2.0, y + 1.0, x + max(width - 2.0, 4.0), y + max(height - 1.0, 4.0)
    )
    ink_color = (0.06, 0.09, 0.16)

    if multiline:
        for font_size in (10.0, 9.0, 8.0, 7.0, 6.0):
            rc = page.insert_textbox(
                rect,
                text,
                fontsize=font_size,
                fontname="helv",
                color=ink_color,
                align=fitz.TEXT_ALIGN_LEFT,
            )
            if rc >= 0:
                return

    # Single-line placement (or fallback when textbox height is too tight for
    # PyMuPDF's line-height multiplier). Scale font size down if the string is
    # wide relative to the box width.
    if height <= 13.0:
        base_font_size = min(max(height * 0.74, 7.5), 9.0)
    else:
        base_font_size = min(max(height * 0.58, 7.0), 11.0)
    estimated_char_width = base_font_size * 0.52
    max_chars_at_base = max(int((width - 4.0) / max(estimated_char_width, 1.0)), 1)
    if len(text) > max_chars_at_base and len(text) > 0:
        scaled = base_font_size * (max_chars_at_base / len(text))
        font_size = max(scaled, 6.0)
    else:
        font_size = base_font_size

    if height <= 13.0:
        baseline_y = y + height - 1.8
    else:
        baseline_y = y + min(height - 2.5, (height + font_size * 0.72) / 2.0)

    if mask_dots:
        text_w = fitz.get_text_length(text, fontname="helv", fontsize=font_size)
        mask_rect = fitz.Rect(
            x,
            y + 1.0,
            min(x + text_w + 5.0, x + width),
            y + height,
        )
        shape = page.new_shape()
        shape.draw_rect(mask_rect)
        shape.finish(width=0, color=None, fill=(1.0, 1.0, 1.0))
        shape.commit()

    page.insert_text(
        fitz.Point(x + 2.0, baseline_y),
        text,
        fontsize=font_size,
        fontname="helv",
        color=ink_color,
    )
