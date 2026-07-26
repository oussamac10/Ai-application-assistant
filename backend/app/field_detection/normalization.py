"""Provider-independent result shaping: safe field names, low-confidence
downgrading, deduplication, and deterministic ordering.

Kept separate from any single provider so both the mock and local providers
(and any future one) can share the exact same normalization guarantees.
"""

from __future__ import annotations

import re

from app.field_detection.constants import LOW_CONFIDENCE_THRESHOLD
from app.field_detection.providers.base import DetectedFieldCandidate

_UNSAFE_NAME_CHARS = re.compile(r"[^a-z0-9]+")


def normalize_field_name(label: str) -> str:
    """Builds a safe, deterministic normalized_name from a label string."""
    lowered = label.strip().lower()
    slug = _UNSAFE_NAME_CHARS.sub("_", lowered).strip("_")
    return slug or "field"


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
) -> list[DetectedFieldCandidate]:
    """Orders by page, then vertical position, then horizontal position —
    falling back to candidate_key for candidates with no known position."""

    def sort_key(candidate: DetectedFieldCandidate) -> tuple[int, float, float, str]:
        box = candidate.input_bounding_box or candidate.label_bounding_box
        y = box.y if box else float("inf")
        x = box.x if box else float("inf")
        return (candidate.page_number, y, x, candidate.candidate_key)

    return sorted(candidates, key=sort_key)
