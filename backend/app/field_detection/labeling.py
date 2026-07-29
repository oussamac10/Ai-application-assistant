"""Label detection and label/input-area association.

Internal to the local rules-based provider — these are intermediate shapes,
not part of the provider-independent contract in providers/base.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from app.field_detection.classification import is_blank_run
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
    # True when this segment carries its own fillable-blank marker (a run
    # of dots/underscores/etc, see classification.is_blank_run) — either
    # after a colon, or (no colon at all) split from a plain label like
    # "IBAN ________________" that relies on layout, not punctuation, to
    # mark where the label ends and the input area begins.
    has_blank_marker: bool = False
    # True when a *sibling* segment on the same physical line is itself a
    # blank run. Real forms very commonly render "Name:" and its dotted
    # input area far enough apart that segment splitting separates them
    # ("Name:" | "…………………"), so the label segment has no marker of its own
    # yet is unambiguously a field. Requiring one of these two signals is
    # what keeps a colon-terminated *prose* line (e.g. "wird folgender
    # Mietvertrag geschlossen:") from being mistaken for a field label.
    has_blank_sibling: bool = False
    tokens: tuple[DetectionToken, ...] = field(default_factory=tuple)


def _split_on_blank_marker(
    tokens: list[DetectionToken],
) -> tuple[str, str, bool] | None:
    """For a colon-less segment, finds the first blank-run token and splits
    the label from it. Returns None if no blank-run token is present or the
    label portion would be empty (a line that is itself just a blank run,
    e.g. a decorative separator, is not a field on its own)."""
    for index, token in enumerate(tokens):
        if is_blank_run(token.text):
            label_tokens = tokens[:index]
            trailing_tokens = tokens[index:]
            label_text = " ".join(t.text for t in label_tokens).strip()
            trailing_text = " ".join(t.text for t in trailing_tokens).strip()
            if not label_text:
                return None
            return label_text, trailing_text, True
    return None


def _phrase_from_segment(
    page_number: int, segment_tokens: list[DetectionToken]
) -> LinePhrase:
    full_text = " ".join(t.text for t in segment_tokens)
    box = union_bounding_box([t.bounding_box for t in segment_tokens])
    source = segment_tokens[0].source

    has_colon = ":" in full_text
    has_blank_marker = False
    if has_colon:
        before, _, after = full_text.partition(":")
        label_text, trailing = before.strip(), after.strip()
        has_blank_marker = bool(trailing) and any(
            is_blank_run(part) for part in trailing.split()
        )
    else:
        split = _split_on_blank_marker(segment_tokens)
        if split is not None:
            label_text, trailing, has_blank_marker = split
        else:
            label_text, trailing = full_text.strip(), ""

    return LinePhrase(
        text=label_text,
        bounding_box=box,
        page_number=page_number,
        source=source,
        has_colon=has_colon,
        trailing_text=trailing,
        has_blank_marker=has_blank_marker,
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
        phrases = [_phrase_from_segment(page_number, segment) for segment in segments]
        # A blank-run segment anywhere on the line makes every other
        # segment on that line a blank-adjacent label candidate.
        if any(is_blank_run(p.text) for p in phrases if not p.has_blank_marker):
            phrases = [
                replace(p, has_blank_sibling=True) if not is_blank_run(p.text) else p
                for p in phrases
            ]
        groups.append(phrases)
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
