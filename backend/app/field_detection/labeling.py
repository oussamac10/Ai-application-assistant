"""Label detection and label/input-area association.

Internal to the local rules-based provider — these are intermediate shapes,
not part of the provider-independent contract in providers/base.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.field_detection.geometry import (
    DEFAULT_PROXIMITY_GAP,
    group_tokens_into_lines,
    is_above,
    is_left_of,
    split_line_into_segments,
    union_bounding_box,
)
from app.field_detection.providers.base import BoundingBox, DetectionToken


@dataclass(frozen=True)
class LinePhrase:
    text: str
    bounding_box: BoundingBox
    page_number: int
    source: str  # the dominant token source contributing to this line
    has_colon: bool = False
    trailing_text: str = ""  # text on the same line after the colon, if any
    tokens: tuple[DetectionToken, ...] = field(default_factory=tuple)


def _phrase_from_segment(
    page_number: int, segment_tokens: list[DetectionToken]
) -> LinePhrase:
    full_text = " ".join(t.text for t in segment_tokens)
    box = union_bounding_box([t.bounding_box for t in segment_tokens])
    source = segment_tokens[0].source

    has_colon = ":" in full_text
    if has_colon:
        before, _, after = full_text.partition(":")
        label_text, trailing = before.strip(), after.strip()
    else:
        label_text, trailing = full_text.strip(), ""

    return LinePhrase(
        text=label_text,
        bounding_box=box,
        page_number=page_number,
        source=source,
        has_colon=has_colon,
        trailing_text=trailing,
        tokens=tuple(segment_tokens),
    )


def build_line_groups(
    page_number: int, tokens: tuple[DetectionToken, ...]
) -> list[list[LinePhrase]]:
    """Groups a page's tokens into visual lines, then splits each line into
    segments (see split_line_into_segments). Each physical line becomes one
    list of one-or-more LinePhrase segments — callers that care about the
    grouping (e.g. choice-group detection) use this; callers that only need
    a flat list use build_line_phrases below.
    """
    groups: list[list[LinePhrase]] = []
    for line_tokens in group_tokens_into_lines(tokens):
        segments = split_line_into_segments(line_tokens)
        groups.append(
            [_phrase_from_segment(page_number, segment) for segment in segments]
        )
    return groups


def build_line_phrases(
    page_number: int, tokens: tuple[DetectionToken, ...]
) -> list[LinePhrase]:
    """Flat variant of build_line_groups, for callers (e.g. AcroForm label
    lookup) that don't need physical-line grouping."""
    return [
        phrase for group in build_line_groups(page_number, tokens) for phrase in group
    ]


def find_nearest_label_for_box(
    target: BoundingBox,
    phrases: list[LinePhrase],
    max_gap: float = DEFAULT_PROXIMITY_GAP,
) -> LinePhrase | None:
    """Finds the best label phrase for a given input area: prefers a label
    immediately to the left, falls back to one directly above."""
    left_candidates = [
        p for p in phrases if is_left_of(p.bounding_box, target, max_gap)
    ]
    if left_candidates:
        return min(
            left_candidates,
            key=lambda p: target.x - (p.bounding_box.x + p.bounding_box.width),
        )

    above_candidates = [p for p in phrases if is_above(p.bounding_box, target, max_gap)]
    if above_candidates:
        return min(
            above_candidates,
            key=lambda p: target.y - (p.bounding_box.y + p.bounding_box.height),
        )

    return None
