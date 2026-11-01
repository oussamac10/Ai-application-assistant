"""Provider-independent result shaping: safe field names, low-confidence
downgrading, deduplication, and deterministic ordering.

Kept separate from any single provider so both the mock and local providers
(and any future one) can share the exact same normalization guarantees.
"""

from __future__ import annotations

import hashlib
import re

from app.field_detection.constants import LOW_CONFIDENCE_THRESHOLD
from app.field_detection.providers.base import DetectedFieldCandidate

# Latin-script slug, unchanged from the original implementation. Tried first
# so every existing German/English key stays byte-identical — including the
# ones that fold awkwardly ("Straße" -> "stra_e").
_ASCII_NAME_CHARS = re.compile(r"[^a-z0-9]+")

# Unicode-aware fallback for scripts the ASCII pass erases completely. This is
# the fix for a real collapse: `[^a-z0-9]+` reduced *every* Arabic label to the
# literal "field", so `deduplicate_candidates` merged a 27-field Arabic form
# into a single question whose label was three unrelated fields joined
# together.
_UNICODE_NAME_CHARS = re.compile(r"[^\w]+|_+", re.UNICODE)

# Length bound so a sentence-like label cannot produce an unbounded key.
_MAX_NAME_LENGTH = 60


def normalize_field_name(label: str) -> str:
    """Builds a safe, deterministic normalized_name from a label string.

    The name is an internal identifier and is never displayed. It only has to
    be stable and **distinct** — distinctness is what deduplication relies on,
    and losing it silently merges unrelated fields into one question.
    """
    lowered = label.strip().lower()
    if not lowered:
        return "field"

    ascii_slug = _ASCII_NAME_CHARS.sub("_", lowered).strip("_")
    if ascii_slug:
        return ascii_slug[:_MAX_NAME_LENGTH].strip("_")

    # Nothing survived the Latin-script pass: a non-Latin script (Arabic,
    # Hebrew, Greek, Cyrillic, CJK). Keep the letters rather than discarding
    # the label's entire identity.
    unicode_slug = _UNICODE_NAME_CHARS.sub("_", lowered).strip("_")
    if unicode_slug:
        return unicode_slug[:_MAX_NAME_LENGTH].strip("_")

    # Punctuation only. A shared constant would merge every such field, so
    # derive a deterministic per-label suffix instead.
    digest = hashlib.sha256(lowered.encode("utf-8")).hexdigest()[:8]
    return f"field_{digest}"


def downgrade_low_confidence(
    candidate: DetectedFieldCandidate,
) -> DetectedFieldCandidate:
    """Never let a low-confidence guess claim a specific field_type."""
    if (
        candidate.confidence < LOW_CONFIDENCE_THRESHOLD
        and candidate.field_type != "unknown"
    ):
        return DetectedFieldCandidate(
            candidate_key=candidate.candidate_key,
            page_number=candidate.page_number,
            label=candidate.label,
            normalized_name=candidate.normalized_name,
            field_type="unknown",
            confidence=candidate.confidence,
            source=candidate.source,
            required=candidate.required,
            multiple=candidate.multiple,
            label_bounding_box=candidate.label_bounding_box,
            input_bounding_box=candidate.input_bounding_box,
            options=candidate.options,
            existing_value=candidate.existing_value,
        )
    return candidate


def deduplicate_candidates(
    candidates: list[DetectedFieldCandidate],
) -> list[DetectedFieldCandidate]:
    """Keeps the first (highest-priority, since callers pass candidates in
    priority order) candidate per normalized_name."""
    seen: set[str] = set()
    result: list[DetectedFieldCandidate] = []
    for candidate in candidates:
        if candidate.normalized_name in seen:
            continue
        seen.add(candidate.normalized_name)
        result.append(candidate)
    return result


def sort_candidates_deterministically(
    candidates: list[DetectedFieldCandidate],
    *,
    rtl: bool = False,
) -> list[DetectedFieldCandidate]:
    """Orders by page, visual horizontal row band, and reading direction —
    falling back to candidate_key for candidates with no known position."""
    by_page: dict[int, list[DetectedFieldCandidate]] = {}
    for candidate in candidates:
        by_page.setdefault(candidate.page_number, []).append(candidate)

    ordered: list[DetectedFieldCandidate] = []
    for page_number in sorted(by_page):
        positioned: list[
            tuple[float, float, float, float, float, DetectedFieldCandidate]
        ] = []
        unpositioned: list[DetectedFieldCandidate] = []
        for candidate in by_page[page_number]:
            box = candidate.input_bounding_box or candidate.label_bounding_box
            if box is None:
                unpositioned.append(candidate)
                continue
            h = max(box.height, 1.0)
            w = max(box.width, 1.0)
            y0 = box.y
            y1 = box.y + h
            yc = (y0 + y1) / 2.0
            positioned.append((yc, y0, box.x, box.x + w, y1, candidate))

        positioned.sort(
            key=lambda item: (
                item[0],
                item[1],
                -item[3] if rtl else item[2],
                item[5].candidate_key,
            )
        )

        rows: list[
            tuple[
                float,
                float,
                list[tuple[float, float, float, DetectedFieldCandidate]],
            ]
        ] = []
        for yc, y0, x0, x1, y1, cand in positioned:
            h = y1 - y0
            placed = False
            for r_idx, (ry0, ry1, r_items) in enumerate(rows):
                rh = max(ry1 - ry0, 1.0)
                if max(h, rh) > 36.0 and abs(y0 - ry0) > 4.0:
                    continue
                if any(
                    min(x1, ix1) - max(x0, ix0) > min(x1 - x0, ix1 - ix0) * 0.25
                    for ix0, ix1, _iy0, _ic in r_items
                ):
                    continue
                overlap_y = min(y1, ry1) - max(y0, ry0)
                ryc = (ry0 + ry1) / 2.0
                if overlap_y >= 0.45 * min(h, rh) or abs(yc - ryc) <= 6.0:
                    r_items.append((x0, x1, y0, cand))
                    rows[r_idx] = (min(ry0, y0), max(ry1, y1), r_items)
                    placed = True
                    break
            if not placed:
                rows.append((y0, y1, [(x0, x1, y0, cand)]))

        rows.sort(key=lambda r: (r[0] + r[1]) / 2.0)
        for _ry0, _ry1, r_items in rows:
            r_items.sort(
                key=lambda item: (
                    -item[1] if rtl else item[0],
                    item[2],
                    item[3].candidate_key,
                )
            )
            ordered.extend(item[3] for item in r_items)

        unpositioned.sort(key=lambda c: c.candidate_key)
        ordered.extend(unpositioned)

    return ordered
