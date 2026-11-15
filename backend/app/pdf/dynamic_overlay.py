"""Dynamic coordinate-overlay PDF rendering for uploaded documents (Phase 17).

When a user uploads an arbitrary PDF form, field detection (`app/field_detection`)
identifies candidate fields along with their page number and `input_bounding_box`.
Once the user completes the guided Q&A session and confirms their answers, this
module maps each `FormField` in the dynamic `FormVersion` back to its originating
`DetectedField` and overlays the confirmed `output_value` (and any vector
signatures) onto a copy of the uploaded PDF using PyMuPDF (`fitz`).

Invariants (per `.agents/AGENTS.md` and ADR 0010):
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
from app.pdf.font_support import draw_unicode_text_in_box
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
from app.storage import factory as storage_factory

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FieldLocationInfo:
    """Page and bounding-box location of a dynamically detected form field."""

    page_number: int
    input_bounding_box: dict[str, float] | None
    label_bounding_box: dict[str, float] | None
    source: str
    page_width_pt: float = 595.0
    page_height_pt: float = 842.0


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


def _join_dehyphenated_lines(lines: list[str]) -> str:
    text = ""
    for part in lines:
        part = part.strip()
        if not part:
            continue
        if text.endswith("-") and part[0].islower():
            text = f"{text[:-1]}{part}"
        elif text:
            text = f"{text} {part}"
        else:
            text = part
    return text.strip()


def extract_table_context_for_page(
    db: Session,
    session: FormSession,
    page_number: int,
    table_top_y: float,
    columns: list[tuple[float, float]],
    *,
    row_y_center: float | None = None,
    first_col_x: float | None = None,
) -> tuple[list[str | None], str | None, str | None, str | None]:
    """Extract (column_headers, table_title, table_description, row_label) for a PDF table."""
    if not columns:
        return [], None, None, None

    storage_path: str | None = None
    source_doc_id = getattr(session, "source_document_id", None)
    if source_doc_id:
        source_doc = db.get(SourceDocument, source_doc_id)
        if source_doc:
            storage_path = source_doc.storage_path
    else:
        version = getattr(session, "version", None) or (
            db.get(FormVersion, session.form_version_id)
            if getattr(session, "form_version_id", None)
            else None
        )
        if version:
            storage_path = getattr(version, "source_pdf_storage_path", None)

    if not storage_path:
        return [None] * len(columns), None, None, None

    storage_provider = storage_factory.get_storage_provider()
    if not storage_provider.exists(storage_path):
        return [None] * len(columns), None, None, None

    try:
        import fitz

        with storage_provider.local_path(storage_path) as local_pdf_path:
            doc = fitz.open(local_pdf_path)
            try:
                page_idx = page_number - 1
                if not (0 <= page_idx < doc.page_count):
                    return [None] * len(columns), None, None, None
                page = doc[page_idx]
                words = page.get_text("words")
                text_dict = page.get_text("dict")
            finally:
                doc.close()
    except Exception:
        return [None] * len(columns), None, None, None

    bounds: list[tuple[float, float]] = []
    for idx, (x0, x1) in enumerate(columns):
        left = (columns[idx - 1][1] + x0) / 2.0 if idx > 0 else x0 - 4.0
        right = (
            (x1 + columns[idx + 1][0]) / 2.0 if idx + 1 < len(columns) else x1 + 20.0
        )
        bounds.append((left, right))

    band = [
        w
        for w in words
        if float(w[3]) <= table_top_y + 2.0 and float(w[1]) >= table_top_y - 52.0
    ]

    headers: list[str | None] = []
    min_header_y0 = table_top_y
    for bl, br in bounds:
        col_words = sorted(
            [w for w in band if bl <= (float(w[0]) + float(w[2])) / 2.0 <= br],
            key=lambda w: (round(float(w[1]) / 3.0), float(w[0])),
        )
        lines: list[list[Any]] = []
        for w in col_words:
            if not lines or abs(float(w[1]) - float(lines[-1][0][1])) > 4.0:
                lines.append([w])
            else:
                lines[-1].append(w)

        kept: list[str] = []
        prev_y0: float | None = None
        for line in reversed(lines):
            y0 = min(float(w[1]) for w in line)
            y1 = max(float(w[3]) for w in line)
            if prev_y0 is not None and prev_y0 - y1 > 10.0:
                break
            min_header_y0 = min(min_header_y0, y0)
            kept.append(
                " ".join(str(w[4]) for w in sorted(line, key=lambda w: float(w[0])))
            )
            prev_y0 = y0

        kept.reverse()
        headers.append(_join_dehyphenated_lines(kept) or None)

    dict_lines: list[tuple[float, float, float, float, float, int, str]] = []
    raw_blocks = text_dict.get("blocks", ()) if isinstance(text_dict, dict) else ()
    for block in raw_blocks:
        if not isinstance(block, dict) or block.get("type") != 0:
            continue
        for line in block.get("lines", ()):
            if not isinstance(line, dict):
                continue
            spans = line.get("spans", ())
            if not spans:
                continue
            ltext = "".join(str(s.get("text", "")) for s in spans).strip()
            if not ltext:
                continue
            bx0, by0, bx1, by1 = (float(v) for v in line["bbox"])
            size = float(spans[0].get("size", 0.0))
            flags = int(spans[0].get("flags", 0))
            dict_lines.append((by0, by1, bx0, bx1, size, flags, ltext))

    header_top = min_header_y0 if min_header_y0 < table_top_y else table_top_y - 34.0
    above_lines = sorted(
        [
            ln
            for ln in dict_lines
            if ln[1] <= header_top - 4.0 and ln[0] >= header_top - 160.0
        ],
        key=lambda ln: (round(ln[0] / 3.0), ln[2]),
    )
    sizes = sorted(ln[4] for ln in dict_lines)
    median_size = sizes[len(sizes) // 2] if sizes else 9.0

    table_title: str | None = None
    table_description: str | None = None
    heading_y0: float | None = None
    for ln in reversed(above_lines):
        is_bold = bool(ln[5] & 16)
        is_larger = ln[4] >= median_size + 1.5
        if (is_bold or is_larger) and len(ln[6]) >= 4:
            same_y = [other for other in above_lines if abs(other[0] - ln[0]) <= 3.0]
            table_title = " ".join(
                o[6] for o in sorted(same_y, key=lambda o: o[2])
            ).strip()
            heading_y0 = ln[0]
            break

    if heading_y0 is not None:
        desc_lines = [
            ln[6]
            for ln in above_lines
            if ln[0] > heading_y0 + 5.0 and ln[1] <= header_top - 4.0
        ]
        if desc_lines:
            desc_full = _join_dehyphenated_lines(desc_lines)
            if len(desc_full) > 320:
                cut = desc_full[:320].rfind(". ")
                desc_full = (
                    desc_full[: cut + 1]
                    if cut > 80
                    else f"{desc_full[:317].rstrip()}..."
                )
            table_description = desc_full or None

    row_label: str | None = None
    if row_y_center is not None and first_col_x is not None:
        import re

        left_tokens = [
            ln[6]
            for ln in dict_lines
            if abs(((ln[0] + ln[1]) / 2.0) - row_y_center) <= 10.0
            and ln[3] <= first_col_x + 2.0
        ]
        if left_tokens:
            raw_row = " ".join(left_tokens).strip()
            cleaned = re.sub(r"^\d+\.?\s*", "", raw_row).strip()
            if cleaned and any(ch.isalpha() for ch in cleaned):
                row_label = cleaned

    return headers, table_title, table_description, row_label


def extract_table_column_headers_for_page(
    db: Session,
    session: FormSession,
    page_number: int,
    table_top_y: float,
    columns: list[tuple[float, float]],
) -> list[str | None]:
    """Extract per-column header text directly above row 1 of a table on a PDF page."""
    headers, _, _, _ = extract_table_context_for_page(
        db, session, page_number, table_top_y, columns
    )
    return headers


def get_all_field_boxes_for_session(
    db: Session,
    session: FormSession,
) -> dict[str, tuple[int, dict[str, float]]]:
    """Return {field.key: (page_number, bbox_dict)} for all fields in a session."""
    version = session.version or db.get(FormVersion, session.form_version_id)
    if not version or not version.fields:
        return {}

    result: dict[str, tuple[int, dict[str, float]]] = {}
    if not session.source_document_id:
        for field in version.fields:
            cfg = field.configuration or {}
            bbox = cfg.get("bbox")
            if bbox and len(bbox) == 4:
                x0, y0, x1, y1 = (
                    float(bbox[0]),
                    float(bbox[1]),
                    float(bbox[2]),
                    float(bbox[3]),
                )
                result[field.key] = (
                    int(cfg.get("page", 1)),
                    {
                        "x": round(x0, 1),
                        "y": round(y0, 1),
                        "width": round(max(x1 - x0, 10.0), 1),
                        "height": round(max(y1 - y0, 10.0), 1),
                    },
                )
        return result

    source_doc = db.get(SourceDocument, session.source_document_id)
    if not source_doc:
        return {}
    detection = get_latest_completed_detection(db, source_doc.id)
    if not detection or not detection.fields:
        return {}

    mapping = map_form_fields_to_detected_fields(
        list(version.fields), list(detection.fields)
    )
    for field_key, detected in mapping.items():
        raw = detected.input_bounding_box
        if not raw:
            continue
        try:
            box = {
                "x": float(raw["x"]),
                "y": float(raw["y"]),
                "width": float(raw["width"]),
                "height": float(raw["height"]),
            }
        except (KeyError, TypeError, ValueError):
            continue
        result[field_key] = (int(detected.page_number or 1), box)
    return result


def get_field_location_for_session(
    db: Session,
    session: FormSession,
    field: FormField,
) -> tuple[FieldLocationInfo | None, Any | None]:
    """Looks up the document and bounding-box metadata for a single field in a session."""
    if not session.source_document_id:
        version = session.version or db.get(FormVersion, session.form_version_id)
        if not version or not version.source_pdf_storage_path:
            return None, None

        cfg = field.configuration or {}
        page_num = int(cfg.get("page", 1))
        bbox = cfg.get("bbox")

        page_w = 595.0
        page_h = 842.0
        page_count = 1

        storage_provider = storage_factory.get_storage_provider()
        if storage_provider.exists(version.source_pdf_storage_path):
            try:
                import fitz

                with storage_provider.local_path(
                    version.source_pdf_storage_path
                ) as local_pdf_path:
                    doc = fitz.open(local_pdf_path)
                    try:
                        page_count = doc.page_count
                        page_idx = page_num - 1
                        if 0 <= page_idx < doc.page_count:
                            rect = doc[page_idx].rect
                            page_w = float(rect.width)
                            page_h = float(rect.height)
                    finally:
                        doc.close()
            except Exception:
                pass

        input_box = None
        if bbox and len(bbox) == 4:
            x0, y0, x1, y1 = (
                float(bbox[0]),
                float(bbox[1]),
                float(bbox[2]),
                float(bbox[3]),
            )
            input_box = {
                "x": round(x0, 1),
                "y": round(y0, 1),
                "width": round(max(x1 - x0, 10.0), 1),
                "height": round(max(y1 - y0, 10.0), 1),
            }

        location = FieldLocationInfo(
            page_number=page_num,
            input_bounding_box=input_box,
            label_bounding_box=None,
            source="template_schema",
            page_width_pt=page_w,
            page_height_pt=page_h,
        )

        class _VirtualDoc:
            def __init__(self, filename: str, count: int) -> None:
                self.original_filename = filename
                self.page_count = count

        doc_name = (
            f"{version.template.name}.pdf"
            if version.template and version.template.name
            else "official_form.pdf"
        )
        return location, _VirtualDoc(doc_name, page_count)

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

    page_w = 595.0
    page_h = 842.0
    effective_in = _clean_box(detected.input_bounding_box)
    effective_lbl = _clean_box(detected.label_bounding_box)
    ocr_dims = _load_ocr_page_dimensions(db, source_doc.id)

    storage_provider = storage_factory.get_storage_provider()
    if source_doc.storage_path and storage_provider.exists(source_doc.storage_path):
        try:
            import fitz

            with storage_provider.local_path(source_doc.storage_path) as local_pdf_path:
                doc = fitz.open(local_pdf_path)
                try:
                    page_idx = detected.page_number - 1
                    if 0 <= page_idx < doc.page_count:
                        rect = doc[page_idx].rect
                        page_w = float(rect.width)
                        page_h = float(rect.height)
                finally:
                    doc.close()

                try:
                    native_doc = extract_native_document_input(local_pdf_path)
                    page_tokens: Sequence[Any] = ()
                    for p in native_doc.pages:
                        if p.page_number == detected.page_number:
                            page_tokens = p.tokens
                            break
                    raw_eff = _resolve_effective_input_box(
                        detected, field.field_type, page_tokens
                    )
                    if raw_eff:
                        effective_in = _clean_box(raw_eff)
                except Exception:
                    pass
        except Exception:
            pass

    if effective_in:
        resolved = _resolve_pdf_rect(
            effective_in,
            source=detected.source,
            page_number=detected.page_number,
            pdf_page_width=page_w,
            pdf_page_height=page_h,
            ocr_dims=ocr_dims,
        )
        if resolved is not None:
            rx, ry, rw, rh = resolved
            if (
                field.field_type
                not in (
                    "multiline_text",
                    "signature",
                    "multiple_choice",
                    "single_choice",
                )
                and 17.0 <= rh <= 24.0
            ):
                ry = ry + (rh - 14.5)
                rh = 14.5
            effective_in = {
                "x": rx,
                "y": ry,
                "width": rw,
                "height": rh,
            }

    if effective_lbl:
        resolved_lbl = _resolve_pdf_rect(
            effective_lbl,
            source=detected.source,
            page_number=detected.page_number,
            pdf_page_width=page_w,
            pdf_page_height=page_h,
            ocr_dims=ocr_dims,
        )
        if resolved_lbl is not None:
            lx, ly, lw, lh = resolved_lbl
            effective_lbl = {
                "x": lx,
                "y": ly,
                "width": lw,
                "height": lh,
            }

    return (
        FieldLocationInfo(
            page_number=detected.page_number,
            input_bounding_box=effective_in,
            label_bounding_box=effective_lbl,
            source=detected.source,
            page_width_pt=page_w,
            page_height_pt=page_h,
        ),
        source_doc,
    )


def render_session_page_preview_png(
    db: Session,
    session: FormSession,
    page_number: int,
) -> bytes | None:
    """Renders 1-indexed `page_number` of the session's PDF document
    to a PNG byte buffer at 144 DPI for the live split-screen field preview.
    """
    if page_number < 1:
        return None

    storage_path = None
    if session.source_document_id:
        source_doc = db.get(SourceDocument, session.source_document_id)
        if source_doc and source_doc.storage_path:
            storage_path = source_doc.storage_path
    else:
        version = session.version or db.get(FormVersion, session.form_version_id)
        if version and version.source_pdf_storage_path:
            storage_path = version.source_pdf_storage_path

    if not storage_path:
        return None

    storage_provider = storage_factory.get_storage_provider()
    if not storage_provider.exists(storage_path):
        return None

    import fitz

    with storage_provider.local_path(storage_path) as source_path:
        doc = fitz.open(source_path)
        try:
            if page_number > doc.page_count:
                return None
            page = doc[page_number - 1]
            try:
                for w in list(page.widgets() or []):
                    page.delete_widget(w)
            except Exception:
                pass
            pix = page.get_pixmap(dpi=144, alpha=False)
            return bytes(pix.tobytes("png"))
        finally:
            doc.close()


def has_exportable_dynamic_document(db: Session, session: FormSession) -> bool:
    """Returns True when `session` is linked to an exportable dynamic or uploaded PDF.
    This includes:
    1. FormVersion with source_pdf_storage_path and field bounding boxes.
    2. Uploaded SourceDocument in storage with at least one confirmed/usable detected field.
    """
    if session.version and session.version.source_pdf_storage_path:
        storage_provider = storage_factory.get_storage_provider()
        if storage_provider.exists(session.version.source_pdf_storage_path):
            return any(
                bool((f.configuration or {}).get("bbox"))
                for f in session.version.fields
            )

    if not session.source_document_id:
        return False

    source_doc = db.get(SourceDocument, session.source_document_id)
    if not source_doc or not source_doc.storage_path:
        return False

    storage_provider = storage_factory.get_storage_provider()
    if not storage_provider.exists(source_doc.storage_path):
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
            if (
                same_line
                and gap >= 12.0
                and native_page_tokens
                and form_field_type
                not in ("single_choice", "multiple_choice", "boolean")
            ):
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
    include_unconfirmed_preview: bool = False,
) -> PDFRenderResult:
    """Copies the uploaded `source_doc` PDF to `output_path` and overlays all
    confirmed answers at their detected `input_bounding_box` coordinates.
    """
    import fitz

    storage_provider = storage_factory.get_storage_provider()
    if not source_doc.storage_path or not storage_provider.exists(
        source_doc.storage_path
    ):
        raise ValueError("Uploaded source PDF file is no longer available in storage.")

    field_to_detected = map_form_fields_to_detected_fields(
        list(version.fields), list(detection.fields)
    )
    ocr_dims = _load_ocr_page_dimensions(db, source_doc.id)

    native_tokens_by_page: dict[int, tuple[Any, ...]] = {}
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with storage_provider.local_path(source_doc.storage_path) as source_path:
        try:
            native_doc = extract_native_document_input(source_path)
            for p in native_doc.pages:
                native_tokens_by_page[p.page_number] = p.tokens
        except Exception:
            native_tokens_by_page = {}

        shutil.copyfile(source_path, output_path)

    allowed_statuses = (
        ("confirmed", "awaiting_confirmation", "draft", PENDING_MANUAL_SIGNATURE)
        if include_unconfirmed_preview
        else ("confirmed", PENDING_MANUAL_SIGNATURE)
    )

    document = fitz.open(output_path)
    try:
        page_count = document.page_count
        for form_field in sorted(version.fields, key=lambda f: f.position):
            ans = answers_by_field_id.get(form_field.id)
            if not ans or ans.status not in allowed_statuses:
                continue
            if include_unconfirmed_preview and ans.validation_status == "invalid":
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
            if form_field.field_type == "money" and page_tokens:
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
                    stripped_amount = re.sub(
                        r"\s*(?:EUR|EURO|USD|GBP|CHF|MAD|€|\$|£)\b.*$",
                        "",
                        formatted_val,
                        flags=re.IGNORECASE,
                    ).strip()
                    if stripped_amount:
                        formatted_val = stripped_amount

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
    """Draws `text` inside `(x, y, width, height)` in PDF points using embedded
    `NotoSans` / `NotoSansArabic` TrueType fonts (`Identity-H` Type0).
    """
    draw_unicode_text_in_box(
        page,
        x=x,
        y=y,
        width=width,
        height=height,
        text=text,
        multiline=multiline,
        mask_dots=mask_dots,
    )


def render_form_version_overlay_pdf(
    *,
    session: FormSession,
    version: FormVersion,
    answers_by_field_id: dict[str, FormAnswer],
    output_path: Path,
    include_unconfirmed_preview: bool = False,
) -> PDFRenderResult:
    """Copies `version.source_pdf_storage_path` to `output_path` and overlays answers
    directly onto the bounding box coordinates stored in each field's configuration.
    """
    import fitz

    storage_provider = storage_factory.get_storage_provider()
    if not version.source_pdf_storage_path or not storage_provider.exists(
        version.source_pdf_storage_path
    ):
        raise ValueError("Form template PDF file is no longer available in storage.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with storage_provider.local_path(version.source_pdf_storage_path) as source_path:
        shutil.copyfile(source_path, output_path)

    allowed_statuses = (
        ("confirmed", "awaiting_confirmation", "draft", PENDING_MANUAL_SIGNATURE)
        if include_unconfirmed_preview
        else ("confirmed", PENDING_MANUAL_SIGNATURE)
    )

    document = fitz.open(output_path)
    try:
        page_count = document.page_count
        for form_field in sorted(version.fields, key=lambda f: f.position):
            ans = answers_by_field_id.get(form_field.id)
            if not ans or ans.status not in allowed_statuses:
                continue
            if include_unconfirmed_preview and ans.validation_status == "invalid":
                continue

            cfg = form_field.configuration or {}
            bbox = cfg.get("bbox")
            page_num = int(cfg.get("page", 1))
            if not bbox or len(bbox) != 4:
                continue

            page_idx = page_num - 1
            if not (0 <= page_idx < page_count):
                continue

            page = document[page_idx]
            x0, y0, x1, y1 = (
                float(bbox[0]),
                float(bbox[1]),
                float(bbox[2]),
                float(bbox[3]),
            )
            x = x0
            y = y0
            width = max(x1 - x0, 10.0)
            height = max(y1 - y0, 10.0)

            if form_field.field_type == "signature":
                if ans.status == PENDING_MANUAL_SIGNATURE or not ans.normalized_value:
                    continue
                sig_h = max(height, 28.0)
                sig_y = max(0.0, y + height - sig_h)
                sig_box = SignatureBox(
                    page_number=page_num,
                    x=x,
                    y=sig_y,
                    width=width,
                    height=sig_h,
                )
                render_signature(page, sig_box, ans.normalized_value)
                continue

            if form_field.field_type == "boolean":
                raw_bool: object = ans.normalized_value
                if raw_bool is True:
                    _draw_checkbox_mark(page, x, y, min(width, 16.0), min(height, 16.0))
                continue

            option_boxes = cfg.get("option_boxes") if isinstance(cfg, dict) else None
            if (
                form_field.field_type in ("choice", "single_choice", "multiple_choice")
                and isinstance(option_boxes, list)
                and option_boxes
            ):
                raw_norm = ans.normalized_value
                if isinstance(raw_norm, list):
                    selected_tokens = {
                        str(item).strip().lower() for item in raw_norm if item
                    }
                elif raw_norm is not None:
                    selected_tokens = {str(raw_norm).strip().lower()}
                else:
                    selected_tokens = set()

                for opt_box in option_boxes:
                    if not isinstance(opt_box, dict):
                        continue
                    box_coords = opt_box.get("bbox")
                    if not isinstance(box_coords, list) or len(box_coords) != 4:
                        continue
                    box_val = str(opt_box.get("value") or "").strip().lower()
                    box_lbl = str(opt_box.get("label") or "").strip().lower()
                    if (
                        box_val not in selected_tokens
                        and box_lbl not in selected_tokens
                    ):
                        continue
                    target_page_num = int(opt_box.get("page", page_num))
                    if target_page_num < 1 or target_page_num > page_count:
                        continue
                    target_page = document[target_page_num - 1]
                    bx0, by0, bx1, by1 = (
                        float(box_coords[0]),
                        float(box_coords[1]),
                        float(box_coords[2]),
                        float(box_coords[3]),
                    )
                    _draw_checkbox_mark(
                        target_page,
                        bx0,
                        by0,
                        min(max(bx1 - bx0, 8.0), 16.0),
                        min(max(by1 - by0, 8.0), 16.0),
                    )
                continue

            formatted_val = format_field_value(
                field_type=form_field.field_type,
                normalized_value=ans.normalized_value,
                output_value=ans.output_value,
                output_language=session.output_language,
            )
            formatted_val = formatted_val.strip() if formatted_val else ""
            if not formatted_val:
                continue

            _draw_text_in_box(
                page,
                x=x,
                y=y,
                width=width,
                height=height,
                text=formatted_val,
                multiline=(form_field.field_type == "textarea" or height > 36.0),
            )

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

    return PDFRenderResult(
        output_path=output_path,
        file_size=output_path.stat().st_size,
        page_count=page_count,
    )
