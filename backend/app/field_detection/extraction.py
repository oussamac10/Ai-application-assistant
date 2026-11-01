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


def _is_marker_sized_rect(rect: fitz.Rect) -> bool:
    width, height = float(rect.width), float(rect.height)
    if not (_MARKER_MIN_SIZE <= width <= _MARKER_MAX_SIZE):
        return False
    if not (_MARKER_MIN_SIZE <= height <= _MARKER_MAX_SIZE):
        return False
    return abs(width - height) <= _MARKER_SQUARENESS_TOLERANCE * max(width, height)


def _closed_rect_from_four_lines(items: list[Any], start: int) -> fitz.Rect | None:
    """Recognises 4 consecutive `("l", p1, p2)` path items that form a closed
    axis-aligned rectangle."""
    if start + 4 > len(items):
        return None
    chunk = items[start : start + 4]
    if any(it[0] != "l" for it in chunk):
        return None

    h_ys: list[float] = []
    h_spans: list[tuple[float, float]] = []
    v_xs: list[float] = []
    v_spans: list[tuple[float, float]] = []
    for _, p1, p2 in chunk:
        dx = abs(p2.x - p1.x)
        dy = abs(p2.y - p1.y)
        if dy <= 1.2 and dx >= _MARKER_MIN_SIZE:
            h_ys.append((p1.y + p2.y) / 2.0)
            h_spans.append((min(p1.x, p2.x), max(p1.x, p2.x)))
        elif dx <= 1.2 and dy >= _MARKER_MIN_SIZE:
            v_xs.append((p1.x + p2.x) / 2.0)
            v_spans.append((min(p1.y, p2.y), max(p1.y, p2.y)))
        else:
            return None

    if len(h_ys) != 2 or len(v_xs) != 2:
        return None
    x0, x1 = min(v_xs), max(v_xs)
    y0, y1 = min(h_ys), max(h_ys)
    if x1 - x0 < _MARKER_MIN_SIZE or y1 - y0 < _MARKER_MIN_SIZE:
        return None
    if any(abs(hx0 - x0) > 1.5 or abs(hx1 - x1) > 1.5 for hx0, hx1 in h_spans):
        return None
    if any(abs(vy0 - y0) > 1.5 or abs(vy1 - y1) > 1.5 for vy0, vy1 in v_spans):
        return None
    return fitz.Rect(x0, y0, x1, y1)


def _marker_glyph_for_drawing(drawing: dict[str, Any]) -> str | None:
    if drawing.get("type") != "s":
        return None

    rect = drawing.get("rect")
    if rect is None or not _is_marker_sized_rect(rect):
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
_MIN_GRID_CELL_WIDTH = 22.0


def _merge_horizontal_segments(
    segments: list[tuple[float, float, float, float]],
) -> list[tuple[float, float, float, float]]:
    """Merges collinear overlapping horizontal segments `(x0, x1, y, h)`."""
    if not segments:
        return []
    ordered = sorted(segments, key=lambda s: (round(s[2], 1), s[0]))
    merged: list[list[float]] = []
    for x0, x1, y, h in ordered:
        for cur in reversed(merged):
            if abs(y - cur[2]) <= 2.0 and x0 <= cur[1] + 3.0 and x1 >= cur[0] - 3.0:
                cur[0] = min(cur[0], x0)
                cur[1] = max(cur[1], x1)
                cur[3] = max(cur[3], h)
                break
        else:
            merged.append([x0, x1, y, h])
    return [
        (m[0], m[1], m[2], m[3]) for m in sorted(merged, key=lambda s: (s[2], s[0]))
    ]


def _merge_vertical_segments(
    segments: list[tuple[float, float, float]],
) -> list[tuple[float, float, float]]:
    """Merges collinear overlapping vertical segments `(x, y0, y1)`."""
    if not segments:
        return []
    ordered = sorted(segments, key=lambda s: (round(s[0], 1), s[1]))
    merged: list[list[float]] = []
    for x, y0, y1 in ordered:
        for cur in reversed(merged):
            if abs(x - cur[0]) <= 2.0 and y0 <= cur[2] + 3.0 and y1 >= cur[1] - 3.0:
                cur[1] = min(cur[1], y0)
                cur[2] = max(cur[2], y1)
                break
        else:
            merged.append([x, y0, y1])
    return [(m[0], m[1], m[2]) for m in sorted(merged, key=lambda s: (s[0], s[1]))]


def _decompose_vector_primitives(
    drawings: list[dict[str, Any]],
) -> tuple[
    list[tuple[str, fitz.Rect]],
    list[fitz.Rect],
    list[tuple[float, float, float, float]],
    list[tuple[float, float, float]],
]:
    """Splits compound PDF paths into `(markers, boxes, h_segments, v_segments)`."""
    markers: list[tuple[str, fitz.Rect]] = []
    seen_markers: set[tuple[float, float, float, float]] = set()
    boxes: list[fitz.Rect] = []
    h_segments: list[tuple[float, float, float, float]] = []
    v_segments: list[tuple[float, float, float]] = []

    def add_marker(glyph: str, r: fitz.Rect) -> None:
        if r.x0 < 0 or r.y0 < 0:
            return
        key = (round(r.x0, 1), round(r.y0, 1), round(r.width, 1), round(r.height, 1))
        if key not in seen_markers:
            seen_markers.add(key)
            markers.append((glyph, r))

    for drawing in drawings:
        dtype = drawing.get("type")
        drect = drawing.get("rect")
        items = list(drawing.get("items") or [])

        # Whole-drawing marker check first (preserves Bezier radio circles).
        whole_glyph = _marker_glyph_for_drawing(drawing)
        if whole_glyph is not None and drect is not None:
            add_marker(whole_glyph, drect)
            continue

        # Filled thin rules (some exporters render underlines/dividers as thin
        # filled rectangles rather than stroked lines).
        if dtype == "f" and drect is not None:
            if (
                drect.width >= _MIN_REGION_WIDTH
                and drect.height <= _MAX_UNDERLINE_HEIGHT
            ):
                h_segments.append(
                    (drect.x0, drect.x1, (drect.y0 + drect.y1) / 2.0, drect.height)
                )
            elif drect.width <= 3.0 and drect.height >= 10.0:
                v_segments.append(((drect.x0 + drect.x1) / 2.0, drect.y0, drect.y1))
            continue

        if dtype not in ("s", "fs") and drawing.get("color") is None:
            continue

        is_stroked_only = dtype == "s" or drawing.get("fill") is None
        idx = 0
        while idx < len(items):
            closed_rect = _closed_rect_from_four_lines(items, idx)
            if closed_rect is not None:
                idx += 4
                if is_stroked_only and _is_marker_sized_rect(closed_rect):
                    add_marker(_CHECKBOX_GLYPH, closed_rect)
                elif closed_rect.width >= _MIN_REGION_WIDTH:
                    boxes.append(closed_rect)
                continue

            item = items[idx]
            op = item[0]
            if op == "re":
                r = item[1]
                if is_stroked_only and _is_marker_sized_rect(r):
                    add_marker(_CHECKBOX_GLYPH, r)
                elif r.width >= _MIN_REGION_WIDTH:
                    boxes.append(r)
                idx += 1
            elif op == "l":
                p1, p2 = item[1], item[2]
                dx = abs(p2.x - p1.x)
                dy = abs(p2.y - p1.y)
                if dy <= 2.0 and dx >= _MIN_REGION_WIDTH:
                    h_segments.append(
                        (min(p1.x, p2.x), max(p1.x, p2.x), (p1.y + p2.y) / 2.0, dy)
                    )
                elif dx <= 2.0 and dy >= 10.0:
                    v_segments.append(
                        ((p1.x + p2.x) / 2.0, min(p1.y, p2.y), max(p1.y, p2.y))
                    )
                idx += 1
            elif op == "c" and is_stroked_only:
                # Contiguous Bezier curves inside a compound path forming a
                # small closed circle -> radio marker.
                c_end = idx
                pts: list[Any] = []
                while c_end < len(items) and items[c_end][0] == "c":
                    pts.extend(items[c_end][1:5])
                    c_end += 1
                if pts:
                    cx0 = min(pt.x for pt in pts)
                    cy0 = min(pt.y for pt in pts)
                    cx1 = max(pt.x for pt in pts)
                    cy1 = max(pt.y for pt in pts)
                    crect = fitz.Rect(cx0, cy0, cx1, cy1)
                    if (
                        abs(pts[0].x - pts[-1].x) <= 2.0
                        and abs(pts[0].y - pts[-1].y) <= 2.0
                        and _is_marker_sized_rect(crect)
                    ):
                        add_marker(_RADIO_GLYPH, crect)
                idx = c_end
            else:
                idx += 1

    return markers, boxes, h_segments, v_segments


def _extract_ruled_regions(
    page: fitz.Page,
    page_number: int,
    tokens: list[DetectionToken] | None = None,
) -> tuple[RuledRegion, ...]:
    """Extracts drawn underlines, standalone boxes, and 2D vector grid cells."""
    _markers, raw_boxes, raw_h, raw_v = _decompose_vector_primitives(
        page.get_drawings()
    )

    # Non-marker stroked rectangles also contribute their 4 edges as potential
    # grid borders when subdivided by internal lines or stacked into a table.
    box_h: list[tuple[float, float, float, float]] = []
    box_v: list[tuple[float, float, float]] = []
    for r in raw_boxes:
        if r.height >= _MIN_BOX_HEIGHT:
            box_h.append((r.x0, r.x1, r.y0, 0.0))
            box_h.append((r.x0, r.x1, r.y1, 0.0))
            box_v.append((r.x0, r.y0, r.y1))
            box_v.append((r.x1, r.y0, r.y1))

    all_h = _merge_horizontal_segments(raw_h + box_h)
    all_v = _merge_vertical_segments(raw_v + box_v)
    standalone_h = _merge_horizontal_segments(raw_h)

    # 1. Discover enclosed horizontal bands bounded on left & right by vertical
    #    borders.
    enclosed_bands: list[dict[str, Any]] = []
    for i, top in enumerate(all_h):
        tx0, tx1, ty, _th = top
        for j in range(i + 1, len(all_h)):
            bot = all_h[j]
            bx0, bx1, by, _bh = bot
            dy = by - ty
            if dy < 10.0:
                continue
            if dy > 160.0:
                break
            ox0, ox1 = max(tx0, bx0), min(tx1, bx1)
            if ox1 - ox0 < _MIN_REGION_WIDTH:
                continue
            # Skip if an intermediate horizontal rule already splits this span.
            has_mid = any(
                ty + 4.0 < all_h[k][2] < by - 4.0
                and min(ox1, all_h[k][1]) - max(ox0, all_h[k][0]) >= (ox1 - ox0) * 0.7
                for k in range(i + 1, j)
            )
            if has_mid:
                continue

            full_vs = [
                v
                for v in all_v
                if ox0 - 3.0 <= v[0] <= ox1 + 3.0
                and (min(by, v[2]) - max(ty, v[1])) >= dy * 0.72
            ]
            if len(full_vs) < 2:
                continue
            left_x = min(v[0] for v in full_vs)
            right_x = max(v[0] for v in full_vs)
            if right_x - left_x < _MIN_REGION_WIDTH:
                continue

            # Strip narrow outer index columns (e.g. item numbers `1`..`26` at
            # left edge, width < 22pt) so row spans align consistently.
            content_x0 = left_x
            for v in sorted(full_vs, key=lambda s: s[0]):
                if content_x0 < v[0] < content_x0 + _MIN_GRID_CELL_WIDTH:
                    content_x0 = v[0]

            any_interior_v = any(
                content_x0 + 8.0 < v[0] < right_x - 8.0
                and (min(by, v[2]) - max(ty, v[1])) >= 10.0
                for v in all_v
            )
            enclosed_bands.append(
                {
                    "left_x": left_x,
                    "x0": content_x0,
                    "x1": right_x,
                    "y0": ty,
                    "y1": by,
                    "top_idx": i,
                    "bot_idx": j,
                    "has_interior_v": any_interior_v,
                }
            )

    # 2. Keep only genuine 2D grid bands: either split into >=2 columns OR part
    #    of a multi-row vertical table stack (>=2 stacked bands). Standalone
    #    1-cell `re` boxes stay `kind="box"` so `visual_fields` preserves its
    #    single-box text-containment semantics.
    grid_bands: list[dict[str, Any]] = []
    for idx, band in enumerate(enclosed_bands):
        has_stack_neighbour = any(
            other_idx != idx
            and (
                abs(other["y0"] - band["y1"]) <= 3.0
                or abs(band["y0"] - other["y1"]) <= 3.0
            )
            and min(band["x1"], other["x1"]) - max(band["x0"], other["x0"])
            >= _MIN_REGION_WIDTH
            for other_idx, other in enumerate(enclosed_bands)
        )
        if band["has_interior_v"] or has_stack_neighbour:
            grid_bands.append(band)

    used_h_ys = {round(all_h[b["top_idx"]][2], 1) for b in grid_bands} | {
        round(all_h[b["bot_idx"]][2], 1) for b in grid_bands
    }

    # 3. Merge empty single-column ruled continuation bands (lined writing
    #    paper inside a form box) into the preceding single-column band.
    page_tokens = tokens or []

    def _band_has_tokens(x0: float, y0: float, x1: float, y1: float) -> bool:
        for t in page_tokens:
            tb = t.bounding_box
            cx = tb.x + tb.width / 2.0
            cy = tb.y + tb.height / 2.0
            if x0 <= cx <= x1 and y0 + 1.0 <= cy <= y1 - 1.0:
                return True
        return False

    grid_bands.sort(key=lambda b: (b["y0"], b["x0"]))
    merged_bands: list[dict[str, Any]] = []
    for band in grid_bands:
        if (
            merged_bands
            and not band["has_interior_v"]
            and not merged_bands[-1]["has_interior_v"]
            and 10.0 <= (band["y1"] - band["y0"]) <= 34.0
            and abs(band["y0"] - merged_bands[-1]["y1"]) <= 2.5
            and abs(band["x0"] - merged_bands[-1]["x0"]) <= 4.0
            and abs(band["x1"] - merged_bands[-1]["x1"]) <= 4.0
            and not _band_has_tokens(band["x0"], band["y0"], band["x1"], band["y1"])
            and _band_has_tokens(
                merged_bands[-1]["x0"],
                merged_bands[-1]["y0"],
                merged_bands[-1]["x1"],
                merged_bands[-1]["y1"],
            )
        ):
            merged_bands[-1] = {**merged_bands[-1], "y1": band["y1"]}
        else:
            merged_bands.append(band)

    # 4. Split each grid band along full or partial bottom vertical dividers
    #    into `RuledRegion(kind="cell")` regions.
    regions: list[RuledRegion] = []
    for band in merged_bands:
        bx0, bx1, by0, by1 = band["x0"], band["x1"], band["y0"], band["y1"]
        bh = by1 - by0
        interior_vs = [
            v
            for v in all_v
            if bx0 + 8.0 < v[0] < bx1 - 8.0
            and (min(by1, v[2]) - max(by0, v[1])) >= 10.0
        ]
        full_dividers = sorted(
            {v[0] for v in interior_vs if v[1] <= by0 + 8.0 and v[2] >= by1 - 4.0}
        )
        partial_bottom_vs = [
            v for v in interior_vs if v[1] > by0 + 8.0 and v[2] >= by1 - 4.0
        ]

        if not full_dividers and partial_bottom_vs:
            sub_y0 = min(v[1] for v in partial_bottom_vs)
            if sub_y0 - by0 >= 18.0:
                regions.append(
                    RuledRegion(
                        kind="cell",
                        page_number=page_number,
                        bounding_box=BoundingBox(
                            x=max(0.0, bx0),
                            y=max(0.0, by0),
                            width=bx1 - bx0,
                            height=sub_y0 - by0,
                        ),
                    )
                )
            div_xs = sorted({v[0] for v in partial_bottom_vs})
            edges = [bx0, *div_xs, bx1]
            for cx0, cx1 in zip(edges, edges[1:], strict=False):
                if cx1 - cx0 >= _MIN_GRID_CELL_WIDTH and by1 - sub_y0 >= 10.0:
                    regions.append(
                        RuledRegion(
                            kind="cell",
                            page_number=page_number,
                            bounding_box=BoundingBox(
                                x=max(0.0, cx0),
                                y=max(0.0, sub_y0),
                                width=cx1 - cx0,
                                height=by1 - sub_y0,
                            ),
                        )
                    )
        else:
            edges = [bx0, *full_dividers, bx1]
            for cx0, cx1 in zip(edges, edges[1:], strict=False):
                if cx1 - cx0 >= _MIN_GRID_CELL_WIDTH and bh >= _MIN_BOX_HEIGHT:
                    regions.append(
                        RuledRegion(
                            kind="cell",
                            page_number=page_number,
                            bounding_box=BoundingBox(
                                x=max(0.0, cx0),
                                y=max(0.0, by0),
                                width=cx1 - cx0,
                                height=bh,
                            ),
                        )
                    )

    # 5. Emit standalone underlines and non-grid boxes unchanged.
    for x0, x1, y, h in standalone_h:
        if round(y, 1) in used_h_ys:
            continue
        if x1 - x0 >= _MIN_REGION_WIDTH and h <= _MAX_UNDERLINE_HEIGHT:
            regions.append(
                RuledRegion(
                    kind="underline",
                    page_number=page_number,
                    bounding_box=BoundingBox(
                        x=max(0.0, x0),
                        y=max(0.0, y - h / 2.0),
                        width=x1 - x0,
                        height=h,
                    ),
                )
            )

    for r in raw_boxes:
        if not (_MIN_BOX_HEIGHT <= r.height <= _MAX_BOX_HEIGHT):
            continue
        if r.width < _MIN_REGION_WIDTH:
            continue
        overlaps_grid = any(
            min(r.x1, b["x1"]) - max(r.x0, b["left_x"]) >= r.width * 0.6
            and min(r.y1, b["y1"]) - max(r.y0, b["y0"])
            >= min(r.height, b["y1"] - b["y0"]) * 0.6
            for b in merged_bands
        )
        if overlaps_grid:
            continue
        regions.append(
            RuledRegion(
                kind="box",
                page_number=page_number,
                bounding_box=BoundingBox(
                    x=max(0.0, r.x0),
                    y=max(0.0, r.y0),
                    width=r.width,
                    height=r.height,
                ),
            )
        )

    return tuple(regions)


_TICK_GLYPHS = frozenset({"", "x", "✓", "✔", "✗", "✘", "o", "•", "×"})


def _marker_rect_contains_non_tick_text(
    rect: fitz.Rect, text_tokens: list[DetectionToken] | None
) -> bool:
    """True when a small square cell encloses printed text such as an item
    index (`24`, `26`, `b)`) rather than an empty or ticked checkbox."""
    if not text_tokens:
        return False
    for tok in text_tokens:
        tb = tok.bounding_box
        cx = tb.x + tb.width / 2.0
        cy = tb.y + tb.height / 2.0
        if (
            rect.x0 - 0.5 <= cx <= rect.x1 + 0.5
            and rect.y0 - 0.5 <= cy <= rect.y1 + 0.5
            and tok.text.strip().lower() not in _TICK_GLYPHS
        ):
            return True
    return False


def _extract_marker_tokens(
    page: fitz.Page, text_tokens: list[DetectionToken] | None = None
) -> list[DetectionToken]:
    markers, _boxes, _h, _v = _decompose_vector_primitives(page.get_drawings())
    return [
        DetectionToken(
            text=glyph,
            confidence=1.0,
            bounding_box=BoundingBox(
                x=rect.x0, y=rect.y0, width=rect.width, height=rect.height
            ),
            source="native",
        )
        for glyph, rect in markers
        if not _marker_rect_contains_non_tick_text(rect, text_tokens)
    ]


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

            vertical_lines: set[tuple[int, int]] = set()
            for block in page.get_text("dict").get("blocks", []):
                if block.get("type") != 0:
                    continue
                b_no = int(block.get("number", -1))
                for l_no, line in enumerate(block.get("lines", [])):
                    dx, _dy = line.get("dir", (1.0, 0.0))
                    if abs(float(dx)) < 0.5:
                        vertical_lines.add((b_no, l_no))

            tokens: list[DetectionToken] = []
            for x0, y0, x1, y1, text, block_no, line_no, *_rest in page.get_text(
                "words"
            ):
                if (int(block_no), int(line_no)) in vertical_lines:
                    continue
                cleaned = text.strip()
                if not cleaned:
                    continue
                tokens.append(
                    DetectionToken(
                        text=cleaned,
                        confidence=1.0,
                        bounding_box=BoundingBox(
                            x=max(0.0, x0),
                            y=max(0.0, y0),
                            width=max(0.0, x1 - x0),
                            height=max(0.0, y1 - y0),
                        ),
                        source="native",
                    )
                )

            tokens.extend(_extract_marker_tokens(page, text_tokens=tokens))

            pages.append(
                DetectionPageInput(
                    page_number=page_number,
                    width=page.rect.width,
                    height=page.rect.height,
                    rotation=page.rotation,
                    tokens=tuple(tokens),
                    ruled_regions=_extract_ruled_regions(
                        page, page_number, tokens=tokens
                    ),
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
