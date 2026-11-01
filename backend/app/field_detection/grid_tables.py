"""Detects repeated multi-column vector grid tables (such as children,
dependents, residence history, or itemised entries) on flattened PDFs.

When a page contains a header row of `>= 3` bordered cells followed immediately
by `>= 2` data rows sharing identical column dividers whose cells hold only
blank space or checkbox/radio markers, each data row is emitted as flat indexed
optional fields (`<section>_<row>_<column>`) matching `repeated_rows.py` and
`frontend/src/features/form-session/utils/repeatedRows.ts`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from app.field_detection.classification import classify_label, marker_type
from app.field_detection.geometry import union_bounding_box
from app.field_detection.normalization import normalize_field_name
from app.field_detection.option_groups import match_option_set
from app.field_detection.providers.base import (
    BoundingBox,
    DetectedFieldCandidate,
    DetectionPageInput,
    DetectionToken,
    RuledRegion,
)

logger = logging.getLogger(__name__)

_MIN_TABLE_COLUMNS = 3
_MIN_DATA_ROWS = 2
_ROW_Y_TOLERANCE = 2.5
_COL_X_TOLERANCE = 3.5


def _tokens_in_box(
    box: BoundingBox, tokens: list[DetectionToken]
) -> list[DetectionToken]:
    out: list[DetectionToken] = []
    for token in tokens:
        tb = token.bounding_box
        cx = tb.x + tb.width / 2.0
        cy = tb.y + tb.height / 2.0
        if box.x - 1.0 <= cx <= box.x + box.width + 1.0 and (
            box.y - 1.5 <= cy <= box.y + box.height + 1.5
        ):
            out.append(token)
    return out


def _join_wrapped_header_tokens(tokens: list[DetectionToken]) -> str:
    """Joins tokens inside a narrow table header cell, reconnecting soft/hard
    hyphenated line breaks (`männ-` + `lich` -> `männlich`)."""
    text_tokens = [t for t in tokens if marker_type(t.text) is None]
    if not text_tokens:
        return ""

    lines: list[list[DetectionToken]] = []
    for tok in sorted(text_tokens, key=lambda t: (t.bounding_box.y, t.bounding_box.x)):
        cy = tok.bounding_box.y + tok.bounding_box.height / 2.0
        for line in lines:
            ref = line[0].bounding_box
            ref_cy = ref.y + ref.height / 2.0
            if abs(cy - ref_cy) <= max(ref.height, tok.bounding_box.height) * 0.6:
                line.append(tok)
                break
        else:
            lines.append([tok])

    line_strings = [
        " ".join(
            t.text for t in sorted(line, key=lambda item: item.bounding_box.x)
        ).strip()
        for line in lines
    ]
    line_strings = [s for s in line_strings if s]
    if not line_strings:
        return ""

    joined = line_strings[0]
    for nxt in line_strings[1:]:
        if joined.endswith("-") and len(joined) >= 2 and nxt[:1].islower():
            joined = joined[:-1] + nxt
        else:
            joined = f"{joined} {nxt}"
    return joined.strip()


def _group_cells_into_rows(cells: list[RuledRegion]) -> list[list[RuledRegion]]:
    rows: list[list[RuledRegion]] = []
    for cell in sorted(cells, key=lambda r: (r.bounding_box.y, r.bounding_box.x)):
        for row in rows:
            if abs(cell.bounding_box.y - row[0].bounding_box.y) <= _ROW_Y_TOLERANCE:
                row.append(cell)
                break
        else:
            rows.append([cell])
    for row in rows:
        row.sort(key=lambda r: r.bounding_box.x)
    return rows


def _same_columns(row_a: list[RuledRegion], row_b: list[RuledRegion]) -> bool:
    if len(row_a) != len(row_b):
        return False
    for ca, cb in zip(row_a, row_b, strict=False):
        if abs(ca.bounding_box.x - cb.bounding_box.x) > _COL_X_TOLERANCE:
            return False
        if abs(ca.bounding_box.width - cb.bounding_box.width) > _COL_X_TOLERANCE:
            return False
    return True


def detect_vector_grid_tables(
    page: DetectionPageInput,
    section_for_y: Callable[[float], tuple[str, str] | None],
) -> tuple[
    list[DetectedFieldCandidate],
    set[tuple[float, float]],
    list[BoundingBox],
]:
    """Detects repeated multi-column grid tables on `page`.

    Returns `(candidates, claimed_region_coords, claimed_table_boxes)`.
    """
    cell_regions = [r for r in page.ruled_regions if r.kind == "cell"]
    if not cell_regions:
        return [], set(), []

    tokens = list(page.tokens)
    page_source = next((t.source for t in tokens if t.source), "native")
    rows = _group_cells_into_rows(cell_regions)

    candidates: list[DetectedFieldCandidate] = []
    claimed_coords: set[tuple[float, float]] = set()
    claimed_boxes: list[BoundingBox] = []

    r_idx = 0
    while r_idx < len(rows):
        header_row = rows[r_idx]
        if len(header_row) < _MIN_TABLE_COLUMNS:
            r_idx += 1
            continue

        header_labels = [
            _join_wrapped_header_tokens(_tokens_in_box(c.bounding_box, tokens))
            for c in header_row
        ]
        non_empty_headers = sum(1 for lbl in header_labels if len(lbl) >= 2)
        if non_empty_headers * 2 < len(header_row):
            r_idx += 1
            continue

        data_rows: list[list[RuledRegion]] = []
        cursor = r_idx + 1
        prev_bottom = max(c.bounding_box.y + c.bounding_box.height for c in header_row)
        while cursor < len(rows):
            cand_row = rows[cursor]
            cand_top = min(c.bounding_box.y for c in cand_row)
            if abs(cand_top - prev_bottom) > 3.5 or not _same_columns(
                header_row, cand_row
            ):
                break
            # Data cells in an unfilled repeated table hold zero printed words
            # (only empty space or checkbox/radio markers).
            has_printed_words = False
            for dc in cand_row:
                cell_toks = _tokens_in_box(dc.bounding_box, tokens)
                if any(marker_type(t.text) is None for t in cell_toks):
                    has_printed_words = True
                    break
            if has_printed_words:
                break
            data_rows.append(cand_row)
            prev_bottom = max(
                c.bounding_box.y + c.bounding_box.height for c in cand_row
            )
            cursor += 1

        if len(data_rows) < _MIN_DATA_ROWS:
            r_idx += 1
            continue

        # Claim header + all data rows so downstream passes ignore them.
        all_table_cells = [c for row in [header_row, *data_rows] for c in row]
        for cell in all_table_cells:
            claimed_coords.add(
                (round(cell.bounding_box.x, 1), round(cell.bounding_box.y, 1))
            )
        claimed_boxes.append(
            union_bounding_box([c.bounding_box for c in all_table_cells])
        )

        sec_info = section_for_y(header_row[0].bounding_box.y)
        section_slug, section_display = (
            sec_info if sec_info is not None else ("row", "Row")
        )

        # Determine which columns carry checkbox/radio markers across data rows.
        marker_cols = {
            col_i
            for d_row in data_rows
            for col_i, dc in enumerate(d_row)
            if any(
                marker_type(t.text) is not None
                for t in _tokens_in_box(dc.bounding_box, tokens)
            )
        }

        for row_num, d_row in enumerate(data_rows, start=1):
            col_i = 0
            while col_i < len(d_row):
                if col_i in marker_cols:
                    # Group contiguous marker columns into a single choice cell.
                    run_cols = [col_i]
                    while (
                        run_cols[-1] + 1 < len(d_row)
                        and (run_cols[-1] + 1) in marker_cols
                    ):
                        run_cols.append(run_cols[-1] + 1)

                    opt_labels = tuple(
                        header_labels[c] or f"Option {c + 1}" for c in run_cols
                    )
                    matched_set = match_option_set(opt_labels)
                    if matched_set is not None:
                        col_slug = matched_set.key
                        exclusive = matched_set.exclusive
                    else:
                        col_slug = normalize_field_name("_".join(opt_labels))
                        exclusive = len(opt_labels) == 2

                    marker_boxes = [
                        t.bounding_box
                        for c in run_cols
                        for t in _tokens_in_box(d_row[c].bounding_box, tokens)
                        if marker_type(t.text) is not None
                    ]
                    in_box = (
                        union_bounding_box(marker_boxes)
                        if marker_boxes
                        else union_bounding_box(
                            [d_row[c].bounding_box for c in run_cols]
                        )
                    )
                    hdr_box = union_bounding_box(
                        [header_row[c].bounding_box for c in run_cols]
                    )
                    key = f"{section_slug}_{row_num}_{col_slug}"
                    candidates.append(
                        DetectedFieldCandidate(
                            candidate_key=f"grid-table-{page.page_number}-{r_idx}-{row_num}-{col_i}",
                            page_number=page.page_number,
                            label=f"{section_display} {row_num} — {' / '.join(opt_labels)}",
                            normalized_name=key,
                            field_type="radio" if exclusive else "multiple_choice",
                            confidence=0.85,
                            source=page_source,
                            required=False,
                            multiple=not exclusive,
                            label_bounding_box=hdr_box,
                            input_bounding_box=in_box,
                            options=opt_labels,
                        )
                    )
                    col_i = run_cols[-1] + 1
                    continue

                col_label = header_labels[col_i]
                if not col_label:
                    col_i += 1
                    continue
                dc_box = d_row[col_i].bounding_box
                col_slug = normalize_field_name(col_label)
                key = f"{section_slug}_{row_num}_{col_slug}"
                in_box = BoundingBox(
                    x=dc_box.x + 2.0,
                    y=dc_box.y + 1.5,
                    width=max(dc_box.width - 4.0, 8.0),
                    height=max(dc_box.height - 3.0, 8.0),
                )
                candidates.append(
                    DetectedFieldCandidate(
                        candidate_key=f"grid-table-{page.page_number}-{r_idx}-{row_num}-{col_i}",
                        page_number=page.page_number,
                        label=f"{section_display} {row_num} – {col_label}",
                        normalized_name=key,
                        field_type=classify_label(col_label),
                        confidence=0.8,
                        source=page_source,
                        required=False,
                        label_bounding_box=header_row[col_i].bounding_box,
                        input_bounding_box=in_box,
                    )
                )
                col_i += 1

        logger.info(
            "Vector grid table detected: page=%d columns=%d data_rows=%d",
            page.page_number,
            len(header_row),
            len(data_rows),
        )
        r_idx = cursor

    return candidates, claimed_coords, claimed_boxes
