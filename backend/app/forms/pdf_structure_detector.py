"""Table-per-row and checkbox-choice-group structuring for extracted PDF fields."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from typing import Any

import fitz  # PyMuPDF

_SHORT_YES_NO_TOKENS = {
    "ja",
    "nein",
    "yes",
    "no",
    "oui",
    "non",
    "si",
    "sí",
    "evet",
    "hayir",
    "hayır",
    "tak",
    "ni",
    "ні",
    "да",
    "нет",
    "نعم",
    "لا",
}

_KNOWN_CHOICE_KEYWORDS = _SHORT_YES_NO_TOKENS | {
    "m",
    "w",
    "d",
    "f",
    "mannlich",
    "weiblich",
    "divers",
    "ledig",
    "verheiratet",
    "lebenspartnerschaft",
    "verwitwet",
    "geschieden",
    "getrennt lebend",
    "getrennt",
    "single",
    "married",
    "divorced",
    "widowed",
    "aufenthaltserlaubnis",
    "niederlassungserlaubnis",
    "duldung",
    "sonstiger status",
    "sonstiges",
    "mit",
    "ohne",
}

_EXCLUDED_CHECKBOX_PHRASES = (
    "einzugsbestätigung",
    "auszugsbestätigung",
    "bundesmeldegesetz",
    "unterschrift",
    "signature",
)

_NON_EXCLUSIVE_HINTS = (
    "mehrfach",
    "multiple",
    "zutreffende",
    "several",
    "all that apply",
)
_ITEM_NUM_PREFIX = re.compile(r"^\s*(?:\[\d+\]|\(?\d+[.)]?)\s*")
_LEADING_SECTION_NUM = re.compile(r"^\s*(\d+(?:\.\d+)?)\s+")


def _fold_text(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(stripped.replace("ß", "ss").replace("ı", "i").lower().split())


def _clean_option_label(raw: str) -> str:
    cleaned = _ITEM_NUM_PREFIX.sub("", raw or "").strip()
    cleaned = re.sub(r"^\s*[☐☑✓✔□■\[\]\(\)xX]\s*", "", cleaned).strip()
    return cleaned.strip(" :;,-.")


def _option_value_slug(label: str) -> str:
    low = _fold_text(label)
    slug = re.sub(r"[^a-z0-9]+", "_", low).strip("_")
    return slug or "option"


def _union_bbox(boxes: list[list[float]]) -> list[float]:
    return [
        round(min(b[0] for b in boxes), 1),
        round(min(b[1] for b in boxes), 1),
        round(max(b[2] for b in boxes), 1),
        round(max(b[3] for b in boxes), 1),
    ]


def _center_y(bbox: list[float]) -> float:
    return (bbox[1] + bbox[3]) / 2.0


def _center_x(bbox: list[float]) -> float:
    return (bbox[0] + bbox[2]) / 2.0


def _clean_slug(text: str, max_len: int = 48) -> str:
    s = _fold_text(text)
    s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
    return s[:max_len].strip("_") or "table"


def _cluster_coords(values: list[float], tolerance: float = 2.5) -> list[float]:
    if not values:
        return []
    ordered = sorted(values)
    clusters: list[list[float]] = [[ordered[0]]]
    for val in ordered[1:]:
        if abs(val - clusters[-1][-1]) <= tolerance:
            clusters[-1].append(val)
        else:
            clusters.append([val])
    return [round(sum(c) / len(c), 1) for c in clusters]


def _shorthand_options_from_header(header: str) -> list[dict[str, str]] | None:
    folded = _fold_text(header)
    if any(tok in folded for tok in ("m/w/d", "m w d", "m/f/d", "m f d")):
        return [
            {"value": "m", "label": "m"},
            {"value": "w", "label": "w"},
            {"value": "d", "label": "d"},
        ]
    if "ja/nein" in folded or "yes/no" in folded:
        return [
            {"value": "ja", "label": "Ja"},
            {"value": "nein", "label": "Nein"},
        ]
    return None


def _text_in_rect(
    words: list[tuple[Any, ...]],
    x0: float,
    y0: float,
    x1: float,
    y1: float,
) -> str:
    hits = [
        (w[1], w[0], str(w[4]))
        for w in words
        if w[2] >= x0 and w[0] <= x1 and w[3] >= y0 and w[1] <= y1
    ]
    hits.sort(key=lambda item: (round(item[0] / 4.0), item[1]))
    return " ".join(item[2] for item in hits).strip()


def _detect_heading_above(
    words: list[tuple[Any, ...]],
    x0: float,
    top_y: float,
    x1: float,
    max_lookback: float = 115.0,
) -> tuple[str | None, str | None]:
    """Return `(table_title, table_description)` from lines just above a table."""
    lines_by_y: dict[int, list[tuple[float, float, str]]] = {}
    for w in words:
        wx0, wy0, wx1, wy1, text = (
            float(w[0]),
            float(w[1]),
            float(w[2]),
            float(w[3]),
            str(w[4]),
        )
        if (
            wy1 <= top_y + 2.0
            and wy0 >= top_y - max_lookback
            and wx1 >= x0 - 30.0
            and wx0 <= x1 + 40.0
        ):
            key = round(wy0 / 5.0)
            lines_by_y.setdefault(key, []).append((wx0, wy0, text))

    if not lines_by_y:
        return None, None

    sorted_lines: list[tuple[float, str]] = []
    for k in sorted(lines_by_y.keys(), reverse=True):
        parts = sorted(lines_by_y[k], key=lambda item: item[0])
        line_text = " ".join(p[2] for p in parts).strip()
        if line_text:
            sorted_lines.append((parts[0][1], line_text))

    title: str | None = None
    desc_lines: list[str] = []
    for _y, line_txt in sorted_lines:
        if _LEADING_SECTION_NUM.match(line_txt):
            title = line_txt
            break
        desc_lines.append(line_txt)

    if title is None and sorted_lines:
        title = sorted_lines[-1][1]
        desc_lines = [line for _, line in sorted_lines[:-1]]

    description = " ".join(reversed(desc_lines)).strip() if desc_lines else None
    if description and len(description) > 360:
        description = description[:357].rsplit(" ", 1)[0] + "..."
    return title, description


def _merge_radio_groups(
    fields: list[dict[str, Any]], page_num: int
) -> list[dict[str, Any]]:
    """Bundle radio buttons sharing raw_field_name into single_choice fields."""
    radio_buckets: dict[str, list[dict[str, Any]]] = {}
    passthrough: list[dict[str, Any]] = []

    for f in fields:
        raw_name = str(f.get("raw_field_name") or "").strip()
        if f.get("is_radio") and raw_name:
            radio_buckets.setdefault(raw_name, []).append(f)
        else:
            passthrough.append(f)

    merged: list[dict[str, Any]] = list(passthrough)
    for raw_name, group in radio_buckets.items():
        if len(group) == 1:
            single = dict(group[0])
            single["field_type"] = "single_choice"
            merged.append(single)
            continue

        group.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))
        options: list[dict[str, str]] = []
        option_boxes: list[dict[str, Any]] = []
        boxes: list[list[float]] = []
        seen_vals: set[str] = set()

        for g in group:
            lbl = (
                _clean_option_label(str(g.get("label") or ""))
                or f"Option {len(options) + 1}"
            )
            val = _option_value_slug(lbl)
            base = val
            idx = 2
            while val in seen_vals:
                val = f"{base}_{idx}"
                idx += 1
            seen_vals.add(val)
            options.append({"value": val, "label": lbl})
            option_boxes.append(
                {
                    "value": val,
                    "label": lbl,
                    "page": page_num,
                    "bbox": list(g["bbox"]),
                }
            )
            boxes.append(g["bbox"])

        lead = group[0]
        clean_title = re.sub(r"[_\-]+", " ", raw_name).strip().title()
        merged.append(
            {
                "key": _clean_slug(raw_name, max_len=64),
                "label": clean_title or lead["label"],
                "field_type": "single_choice",
                "question_key": None,
                "requiredness": lead.get("requiredness", "unknown"),
                "options": options,
                "option_boxes": option_boxes,
                "bbox": _union_bbox(boxes),
                "page": page_num,
            }
        )

    return merged


def _extract_grid_bands(
    page: fitz.Page,
) -> tuple[float, float, list[tuple[float, float]], list[tuple[float, float]]] | None:
    """Detect the dominant horizontal/vertical line grid on a page when drawn."""
    h_segments: list[tuple[float, float, float]] = []  # (y, x0, x1)
    v_segments: list[tuple[float, float, float]] = []  # (x, y0, y1)

    try:
        drawings = page.get_drawings() or []
    except Exception:
        drawings = []

    for d in drawings:
        rect = d.get("rect")
        for item in d.get("items") or []:
            op = item[0]
            if op == "l":
                p1, p2 = item[1], item[2]
                if abs(p1.y - p2.y) <= 2.5 and abs(p2.x - p1.x) >= 35.0:
                    h_segments.append(
                        (
                            (float(p1.y) + float(p2.y)) / 2.0,
                            min(float(p1.x), float(p2.x)),
                            max(float(p1.x), float(p2.x)),
                        )
                    )
                elif abs(p1.x - p2.x) <= 2.5 and abs(p2.y - p1.y) >= 16.0:
                    v_segments.append(
                        (
                            (float(p1.x) + float(p2.x)) / 2.0,
                            min(float(p1.y), float(p2.y)),
                            max(float(p1.y), float(p2.y)),
                        )
                    )
            elif op == "re":
                r = item[1]
                if r.width >= 35.0 and r.height <= 4.0:
                    h_segments.append(
                        ((float(r.y0) + float(r.y1)) / 2.0, float(r.x0), float(r.x1))
                    )
                elif r.height >= 16.0 and r.width <= 4.0:
                    v_segments.append(
                        ((float(r.x0) + float(r.x1)) / 2.0, float(r.y0), float(r.y1))
                    )
                elif r.width >= 35.0 and r.height >= 8.0:
                    h_segments.append((float(r.y0), float(r.x0), float(r.x1)))
                    h_segments.append((float(r.y1), float(r.x0), float(r.x1)))
                    v_segments.append((float(r.x0), float(r.y0), float(r.y1)))
                    v_segments.append((float(r.x1), float(r.y0), float(r.y1)))
        if rect and rect.width >= 120.0 and rect.height >= 35.0 and not d.get("items"):
            h_segments.append((float(rect.y0), float(rect.x0), float(rect.x1)))
            h_segments.append((float(rect.y1), float(rect.x0), float(rect.x1)))

    if len(h_segments) < 3:
        return None

    # Find widest span representing table bounds
    wide_h = [seg for seg in h_segments if (seg[2] - seg[1]) >= 140.0]
    if len(wide_h) < 3:
        return None

    x0 = min(seg[1] for seg in wide_h)
    x1 = max(seg[2] for seg in wide_h)
    y_coords = _cluster_coords([seg[0] for seg in wide_h], tolerance=2.8)
    if len(y_coords) < 3:
        return None

    row_bands = [
        (y_coords[i], y_coords[i + 1])
        for i in range(len(y_coords) - 1)
        if 8.0 <= (y_coords[i + 1] - y_coords[i]) <= 80.0
    ]
    if len(row_bands) < 2:
        return None

    t_top, t_bot = row_bands[0][0], row_bands[-1][1]
    v_in_table = [
        seg[0]
        for seg in v_segments
        if seg[0] >= x0 - 4.0
        and seg[0] <= x1 + 4.0
        and seg[2] >= t_top
        and seg[1] <= t_bot
    ]
    x_cols = _cluster_coords([x0, *v_in_table, x1], tolerance=3.5)
    col_ranges = [
        (x_cols[i], x_cols[i + 1])
        for i in range(len(x_cols) - 1)
        if (x_cols[i + 1] - x_cols[i]) >= 10.0
    ]
    return x0, x1, row_bands, col_ranges


def _infer_col_metadata(
    header_text: str,
    raw_field_type: str,
    row_index: int,
    infer_fn: Callable[[str, str], tuple[str, str, str | None, str]],
) -> tuple[str, str, str | None, str, list[dict[str, str]] | None]:
    clean_hdr = _ITEM_NUM_PREFIX.sub("", header_text).strip(" :;") or "Feld"
    _, ftype, qkey, req = infer_fn(clean_hdr, raw_field_type)
    shorthand_opts = _shorthand_options_from_header(clean_hdr)
    if shorthand_opts:
        ftype = "single_choice"
        qkey = None

    folded_hdr = _fold_text(clean_hdr)
    if any(tok in folded_hdr for tok in ("staatsangeh", "nationality", "citizen")):
        ftype = "country"
        qkey = "personal.nationality" if row_index == 1 else None

    if row_index >= 2:
        # Strict isolation: household members must never pull applicant's Vault keys
        qkey = None
        req = "optional"

    return clean_hdr, ftype, qkey, req, shorthand_opts


def _bundle_intra_row_checkboxes(
    row_fields: list[dict[str, Any]],
    col_ranges: list[tuple[float, float]],
    words: list[tuple[Any, ...]],
    header_band: tuple[float, float] | None,
    page_num: int,
) -> list[dict[str, Any]]:
    """Bundle adjacent checkboxes inside one table row (e.g., ja / nein) into one choice cell."""
    ordered = sorted(row_fields, key=lambda item: item["bbox"][0])
    used: set[int] = set()
    output: list[dict[str, Any]] = []

    def col_idx_for(bbox: list[float]) -> int:
        cx = _center_x(bbox)
        for idx, (cx0, cx1) in enumerate(col_ranges):
            if cx0 - 3.0 <= cx <= cx1 + 3.0:
                return idx
        return -1

    for i, f in enumerate(ordered):
        if i in used:
            continue
        if f.get("field_type") != "boolean":
            used.add(i)
            output.append(f)
            continue

        group = [f]
        used.add(i)
        c_i = col_idx_for(f["bbox"])

        for j in range(i + 1, len(ordered)):
            if j in used:
                continue
            cand = ordered[j]
            if cand.get("field_type") != "boolean":
                continue
            prev = group[-1]
            same_y = abs(_center_y(cand["bbox"]) - _center_y(prev["bbox"])) <= 12.0
            close_x = (cand["bbox"][0] - prev["bbox"][2]) <= 68.0
            lbl_cand = _fold_text(_clean_option_label(str(cand.get("label") or "")))
            lbl_prev = _fold_text(_clean_option_label(str(prev.get("label") or "")))
            both_short_choice = (
                lbl_cand in _KNOWN_CHOICE_KEYWORDS
                and lbl_prev in _KNOWN_CHOICE_KEYWORDS
            ) or (
                len(lbl_cand.split()) <= 2
                and len(lbl_prev.split()) <= 2
                and (c_i != -1 and col_idx_for(cand["bbox"]) == c_i)
            )
            if same_y and close_x and both_short_choice:
                group.append(cand)
                used.add(j)

        if len(group) == 1:
            output.append(f)
            continue

        boxes = [g["bbox"] for g in group]
        u_bbox = _union_bbox(boxes)
        col_title = ""
        if header_band:
            hy0, hy1 = header_band
            matched_col = next(
                (
                    (cx0, cx1)
                    for cx0, cx1 in col_ranges
                    if cx0 - 3.0 <= _center_x(u_bbox) <= cx1 + 3.0
                ),
                None,
            )
            hx0, hx1 = (
                (matched_col[0] + 1.5, matched_col[1] - 1.5)
                if matched_col
                else (u_bbox[0] - 2.0, u_bbox[2] + 2.0)
            )
            col_title = _text_in_rect(words, hx0, hy0, hx1, hy1)

        options: list[dict[str, str]] = []
        option_boxes: list[dict[str, Any]] = []
        seen_vals: set[str] = set()
        for idx_g, g in enumerate(group):
            gx0, gy0, gx1, gy1 = g["bbox"]
            next_gx0 = group[idx_g + 1]["bbox"][0] if idx_g + 1 < len(group) else None
            right_bound = (next_gx0 - 2.0) if next_gx0 is not None else (gx1 + 48.0)
            local_txt = _clean_option_label(
                _text_in_rect(words, gx1 + 1.0, gy0 - 5.0, right_bound, gy1 + 5.0)
            )
            fallback_txt = _clean_option_label(str(g.get("label") or ""))
            lbl = local_txt or fallback_txt or f"Option {len(options) + 1}"
            val = _option_value_slug(lbl)
            base = val
            suffix = 2
            while val in seen_vals:
                val = f"{base}_{suffix}"
                suffix += 1
            seen_vals.add(val)
            options.append({"value": val, "label": lbl})
            option_boxes.append(
                {
                    "value": val,
                    "label": lbl,
                    "page": page_num,
                    "bbox": list(g["bbox"]),
                }
            )

        output.append(
            {
                "key": f"{group[0]['key']}_choice",
                "label": _ITEM_NUM_PREFIX.sub("", col_title).strip() or "Auswahl",
                "field_type": "single_choice",
                "question_key": None,
                "requiredness": group[0].get("requiredness", "unknown"),
                "options": options,
                "option_boxes": option_boxes,
                "bbox": u_bbox,
                "page": page_num,
            }
        )

    return output


def _group_borderless_table_rows(
    fields: list[dict[str, Any]],
) -> list[list[dict[str, Any]]]:
    """Fallback row clustering when a PDF table has no drawn vector borders."""
    if len(fields) < 4:
        return []
    ordered = sorted(
        fields, key=lambda item: (_center_y(item["bbox"]), item["bbox"][0])
    )
    bands: list[list[dict[str, Any]]] = []
    for f in ordered:
        cy = _center_y(f["bbox"])
        if bands and abs(cy - _center_y(bands[-1][0]["bbox"])) <= 14.0:
            bands[-1].append(f)
        else:
            bands.append([f])

    multi_bands = [
        sorted(b, key=lambda item: item["bbox"][0]) for b in bands if len(b) >= 2
    ]
    if len(multi_bands) < 2:
        return []

    # Require column x0 overlap across adjacent multi-widget rows
    groups: list[list[list[dict[str, Any]]]] = [[multi_bands[0]]]
    for band in multi_bands[1:]:
        prev = groups[-1][-1]
        aligned = sum(
            1
            for b_cell in band
            if any(
                abs(b_cell["bbox"][0] - p_cell["bbox"][0]) <= 24.0 for p_cell in prev
            )
        )
        y_gap = _center_y(band[0]["bbox"]) - _center_y(prev[0]["bbox"])
        if aligned >= 2 and 10.0 <= y_gap <= 72.0:
            groups[-1].append(band)
        else:
            groups.append([band])

    best = max(groups, key=len, default=[])
    return best if len(best) >= 2 else []


def _group_horizontal_choice_clusters(
    remaining_fields: list[dict[str, Any]],
    words: list[tuple[Any, ...]],
    page_num: int,
) -> list[dict[str, Any]]:
    """Bundle standalone adjacent short-label checkboxes (e.g., Familienstand, Aufenthaltsstatus)."""
    booleans = [
        (idx, f)
        for idx, f in enumerate(remaining_fields)
        if f.get("field_type") == "boolean" and not f.get("table")
    ]
    if len(booleans) < 2:
        return remaining_fields

    # Group horizontally aligned short-label checkboxes
    booleans_sorted = sorted(
        booleans,
        key=lambda item: (round(_center_y(item[1]["bbox"]) / 8.0), item[1]["bbox"][0]),
    )
    clusters: list[list[tuple[int, dict[str, Any]]]] = []
    for pos_b, item in enumerate(booleans_sorted):
        idx, f = item
        gx0, gy0, gx1, gy1 = f["bbox"]
        next_x0: float | None = None
        if pos_b + 1 < len(booleans_sorted):
            nb = booleans_sorted[pos_b + 1][1]["bbox"]
            if abs(_center_y(nb) - _center_y(f["bbox"])) <= 12.0:
                next_x0 = float(nb[0])
        right_lim = (next_x0 - 2.0) if next_x0 is not None else (gx1 + 110.0)
        local_lbl = _clean_option_label(
            _text_in_rect(words, gx1 + 1.0, gy0 - 5.0, right_lim, gy1 + 5.0)
        )
        raw_lbl = str(f.get("label") or "")
        low_lbl = (local_lbl or raw_lbl).lower()
        clean_opt = local_lbl or _clean_option_label(raw_lbl)
        if any(excl in low_lbl for excl in _EXCLUDED_CHECKBOX_PHRASES):
            continue
        if len(clean_opt.split()) > 4 or not clean_opt:
            continue

        if clusters:
            prev_idx, prev_f = clusters[-1][-1]
            same_line = abs(_center_y(f["bbox"]) - _center_y(prev_f["bbox"])) <= 12.0
            h_gap = f["bbox"][0] - prev_f["bbox"][2]
            if same_line and 0.0 <= h_gap <= 155.0:
                clusters[-1].append((idx, f))
                continue
        clusters.append([(idx, f)])

    consumed_indices: set[int] = set()
    new_choice_fields: list[dict[str, Any]] = []

    for cl in clusters:
        if len(cl) < 2:
            continue
        # Extract each checkbox's isolated right-hand option text up to the next sibling checkbox
        resolved_labels: list[str] = []
        for idx_c, (_, cf) in enumerate(cl):
            cx0, cy0, cx1, cy1 = cf["bbox"]
            nxt_x0 = cl[idx_c + 1][1]["bbox"][0] if idx_c + 1 < len(cl) else None
            r_lim = (nxt_x0 - 2.0) if nxt_x0 is not None else (cx1 + 110.0)
            loc = _clean_option_label(
                _text_in_rect(words, cx1 + 1.0, cy0 - 5.0, r_lim, cy1 + 5.0)
            )
            fb = _clean_option_label(str(cf.get("label") or ""))
            resolved_labels.append(loc or fb or f"Option {idx_c + 1}")

        opt_tokens = [_fold_text(lbl) for lbl in resolved_labels]
        has_known_opt = any(tok in _KNOWN_CHOICE_KEYWORDS for tok in opt_tokens)
        u_bbox = _union_bbox([item[1]["bbox"] for item in cl])
        heading_txt = _text_in_rect(
            words, u_bbox[0] - 25.0, u_bbox[1] - 32.0, u_bbox[2] + 35.0, u_bbox[1] - 2.0
        )
        heading_clean = _ITEM_NUM_PREFIX.sub("", heading_txt).strip(" :;")
        if not has_known_opt and not heading_clean and len(cl) < 3:
            continue

        is_multi = any(h in _fold_text(heading_clean) for h in _NON_EXCLUSIVE_HINTS)
        options: list[dict[str, str]] = []
        option_boxes: list[dict[str, Any]] = []
        seen_vals: set[str] = set()

        for (orig_idx, f), lbl in zip(cl, resolved_labels, strict=True):
            consumed_indices.add(orig_idx)
            val = _option_value_slug(lbl)
            base = val
            suffix = 2
            while val in seen_vals:
                val = f"{base}_{suffix}"
                suffix += 1
            seen_vals.add(val)
            options.append({"value": val, "label": lbl})
            option_boxes.append(
                {
                    "value": val,
                    "label": lbl,
                    "page": page_num,
                    "bbox": list(f["bbox"]),
                }
            )

        if not heading_clean:
            if all(t in _SHORT_YES_NO_TOKENS for t in opt_tokens):
                heading_clean = "Ja / Nein"
            elif any(
                t in {"ledig", "verheiratet", "geschieden", "verwitwet"}
                for t in opt_tokens
            ):
                heading_clean = "Familienstand"
            elif any(
                t in {"aufenthaltserlaubnis", "niederlassungserlaubnis", "duldung"}
                for t in opt_tokens
            ):
                heading_clean = "Aufenthaltsstatus"
            elif any(
                t in {"m", "w", "d", "mannlich", "weiblich", "divers"}
                for t in opt_tokens
            ):
                heading_clean = "Geschlecht"
            else:
                heading_clean = (
                    f"Auswahl ({options[0]['label']} / {options[1]['label']})"
                )

        new_choice_fields.append(
            {
                "key": _clean_slug(heading_clean, max_len=64),
                "label": heading_clean,
                "field_type": "multiple_choice" if is_multi else "single_choice",
                "question_key": None,
                "requiredness": cl[0][1].get("requiredness", "unknown"),
                "options": options,
                "option_boxes": option_boxes,
                "bbox": u_bbox,
                "page": page_num,
            }
        )

    result = [
        f for idx, f in enumerate(remaining_fields) if idx not in consumed_indices
    ]
    result.extend(new_choice_fields)
    result.sort(key=lambda item: (item["bbox"][1], item["bbox"][0]))
    return result


def structure_pdf_page_fields(
    page: fitz.Page,
    raw_fields: list[dict[str, Any]],
    page_num: int,
    infer_fn: Callable[[str, str], tuple[str, str, str | None, str]],
) -> list[dict[str, Any]]:
    """Group radio sets, table rows, and intra-row/horizontal checkbox choices on a page."""
    if not raw_fields:
        return []

    words = page.get_text("words") or []

    # Pass 1: Radio button groups
    fields = _merge_radio_groups(raw_fields, page_num)

    # Pass 2: Multi-row table detection (vector grid first, borderless column alignment fallback)
    consumed: set[int] = set()
    table_structured: list[dict[str, Any]] = []
    grid = _extract_grid_bands(page)

    if grid:
        table_x0, table_x1, bands, col_ranges = grid
        band_members: list[
            tuple[tuple[float, float], list[tuple[int, dict[str, Any]]]]
        ] = []
        for b in bands:
            by0, by1 = b
            members: list[tuple[int, dict[str, Any]]] = []
            for idx, f in enumerate(fields):
                if idx in consumed:
                    continue
                cy = _center_y(f["bbox"])
                cx = _center_x(f["bbox"])
                if (by0 - 3.0) <= cy <= (by1 + 3.0) and (table_x0 - 6.0) <= cx <= (
                    table_x1 + 6.0
                ):
                    members.append((idx, f))
            band_members.append((b, members))

        data_bands = [(b, m) for b, m in band_members if m]
        if len(data_bands) >= 2:
            first_data_idx = next(i for i, (_, m) in enumerate(band_members) if m)
            header_band = (
                band_members[first_data_idx - 1][0] if first_data_idx > 0 else None
            )
            table_top_y = header_band[0] if header_band else data_bands[0][0][0]
            table_title, table_desc = _detect_heading_above(
                words, table_x0, table_top_y, table_x1
            )
            t_title_clean = table_title or f"Tabelle (Seite {page_num})"
            t_key = _clean_slug(t_title_clean, max_len=40)
            total_rows = len(data_bands)

            for row_pos, ((ry0, ry1), members) in enumerate(data_bands, start=1):
                for idx, _ in members:
                    consumed.add(idx)
                raw_row_items = [m[1] for m in members]
                bundled_row = _bundle_intra_row_checkboxes(
                    raw_row_items, col_ranges, words, header_band, page_num
                )
                row_text = _text_in_rect(words, table_x0, ry0, table_x0 + 180.0, ry1)
                if row_pos == 1 and "antragstell" in row_text.lower():
                    row_label = "Antragstellende Person"
                    row_role = "applicant"
                elif row_pos == 1:
                    row_label = "Zeile 1"
                    row_role = "applicant"
                else:
                    row_label = f"Zeile {row_pos}"
                    row_role = "member"

                for col_idx, cell in enumerate(bundled_row):
                    hdr_txt = ""
                    if header_band:
                        matched_col = next(
                            (
                                (cx0, cx1)
                                for cx0, cx1 in col_ranges
                                if cx0 - 3.0 <= _center_x(cell["bbox"]) <= cx1 + 3.0
                            ),
                            None,
                        )
                        hx0, hx1 = (
                            (matched_col[0] + 1.5, matched_col[1] - 1.5)
                            if matched_col
                            else (cell["bbox"][0] - 2.0, cell["bbox"][2] + 2.0)
                        )
                        hdr_txt = _text_in_rect(
                            words,
                            hx0,
                            header_band[0],
                            hx1,
                            header_band[1],
                        )
                    col_hdr, ftype, qkey, req, shorthand_opts = _infer_col_metadata(
                        hdr_txt or str(cell.get("label") or ""),
                        str(cell.get("field_type") or "string"),
                        row_pos,
                        infer_fn,
                    )
                    updated = dict(cell)
                    updated["field_type"] = (
                        cell["field_type"]
                        if cell.get("field_type")
                        in ("single_choice", "multiple_choice")
                        else ftype
                    )
                    updated["question_key"] = qkey if row_pos == 1 else None
                    updated["requiredness"] = (
                        req if row_pos >= 2 else updated.get("requiredness", req)
                    )
                    if not updated.get("options") and shorthand_opts:
                        updated["options"] = shorthand_opts
                    updated["label"] = col_hdr
                    updated["table"] = {
                        "table_key": t_key,
                        "table_title": t_title_clean,
                        "table_description": table_desc,
                        "row_index": row_pos,
                        "total_rows": total_rows,
                        "row_label": row_label,
                        "row_role": row_role,
                        "col_index": col_idx,
                        "column_header": col_hdr,
                    }
                    table_structured.append(updated)

    # Borderless table fallback when no vector grid grouped anything
    if not consumed:
        borderless_rows = _group_borderless_table_rows(fields)
        if borderless_rows:
            row_ids = {id(cell) for row in borderless_rows for cell in row}
            for idx, f in enumerate(fields):
                if id(f) in row_ids:
                    consumed.add(idx)

            all_row_cells = [cell for row in borderless_rows for cell in row]
            bx0 = min(c["bbox"][0] for c in all_row_cells)
            bx1 = max(c["bbox"][2] for c in all_row_cells)
            by0 = min(c["bbox"][1] for c in all_row_cells)
            header_band = (max(0.0, by0 - 28.0), by0 - 1.0)
            table_title, table_desc = _detect_heading_above(words, bx0, by0 - 22.0, bx1)
            t_title_clean = table_title or f"Tabelle (Seite {page_num})"
            t_key = _clean_slug(t_title_clean, max_len=40)
            total_rows = len(borderless_rows)

            for row_pos, raw_row_items in enumerate(borderless_rows, start=1):
                bundled_row = _bundle_intra_row_checkboxes(
                    raw_row_items, [], words, header_band, page_num
                )
                row_label = (
                    "Antragstellende Person" if row_pos == 1 else f"Zeile {row_pos}"
                )
                row_role = "applicant" if row_pos == 1 else "member"

                for col_idx, cell in enumerate(bundled_row):
                    hdr_txt = _text_in_rect(
                        words,
                        cell["bbox"][0] - 10.0,
                        header_band[0],
                        cell["bbox"][2] + 10.0,
                        header_band[1],
                    )
                    col_hdr, ftype, qkey, req, shorthand_opts = _infer_col_metadata(
                        hdr_txt or str(cell.get("label") or ""),
                        str(cell.get("field_type") or "string"),
                        row_pos,
                        infer_fn,
                    )
                    updated = dict(cell)
                    updated["field_type"] = (
                        cell["field_type"]
                        if cell.get("field_type")
                        in ("single_choice", "multiple_choice")
                        else ftype
                    )
                    updated["question_key"] = qkey if row_pos == 1 else None
                    updated["requiredness"] = (
                        req if row_pos >= 2 else updated.get("requiredness", req)
                    )
                    if not updated.get("options") and shorthand_opts:
                        updated["options"] = shorthand_opts
                    updated["label"] = col_hdr
                    updated["table"] = {
                        "table_key": t_key,
                        "table_title": t_title_clean,
                        "table_description": table_desc,
                        "row_index": row_pos,
                        "total_rows": total_rows,
                        "row_label": row_label,
                        "row_role": row_role,
                        "col_index": col_idx,
                        "column_header": col_hdr,
                    }
                    table_structured.append(updated)

    # Pass 3: Remaining non-table fields -> standalone horizontal choice clusters
    remaining = [f for idx, f in enumerate(fields) if idx not in consumed]
    remaining_structured = _group_horizontal_choice_clusters(remaining, words, page_num)

    # Keep each table's rows & columns contiguous at the table's vertical position,
    # while sorting non-table fields top-to-bottom, left-to-right.
    table_min_y: dict[str, float] = {}
    for item in table_structured:
        t_meta = item.get("table")
        if isinstance(t_meta, dict) and t_meta.get("table_key"):
            tk = str(t_meta["table_key"])
            y_val = float(item["bbox"][1])
            if tk not in table_min_y or y_val < table_min_y[tk]:
                table_min_y[tk] = y_val

    combined = remaining_structured + table_structured

    def _sort_key(item: dict[str, Any]) -> tuple[float, int, int, float]:
        t_meta = item.get("table")
        if isinstance(t_meta, dict) and t_meta.get("table_key"):
            tk = str(t_meta["table_key"])
            return (
                table_min_y.get(tk, float(item["bbox"][1])),
                int(t_meta.get("row_index", 0)),
                int(t_meta.get("col_index", 0)),
                float(item["bbox"][0]),
            )
        return (
            float(round(float(item["bbox"][1]) / 6.0) * 6),
            0,
            0,
            float(item["bbox"][0]),
        )

    combined.sort(key=_sort_key)
    for item in combined:
        item.pop("is_radio", None)
        item.pop("raw_field_name", None)
    return combined
