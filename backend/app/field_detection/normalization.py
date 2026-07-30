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
) -> list[DetectedFieldCandidate]:
    """Orders by page, then vertical position, then horizontal position —
    falling back to candidate_key for candidates with no known position."""

    def sort_key(candidate: DetectedFieldCandidate) -> tuple[int, float, float, str]:
        box = candidate.input_bounding_box or candidate.label_bounding_box
        y = box.y if box else float("inf")
        x = box.x if box else float("inf")
        return (candidate.page_number, y, x, candidate.candidate_key)

    return sorted(candidates, key=sort_key)
