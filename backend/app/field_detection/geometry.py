"""Coordinate normalization and proximity calculations shared by the
rules-based local provider. Operates purely on BoundingBox geometry, so the
same logic applies whether coordinates are in PDF point space or OCR pixel
space — the caller never mixes the two under one comparison.
"""

from __future__ import annotations

from app.field_detection.providers.base import BoundingBox, DetectionToken

# A word belongs to the same visual line as another if their vertical
# centers fall within this fraction of the shorter token's height.
_LINE_CLUSTER_TOLERANCE = 0.6

# How far (in the same units as the bounding boxes) a label may sit from an
# input area and still be considered "next to" it.
DEFAULT_PROXIMITY_GAP = 40.0

# Within one physical line, a horizontal gap larger than this multiple of
# the token height signals a new field's label starting (e.g. two labels
# such as "Signature:" and "Date:" sharing one line, separated by blank
# input space) rather than normal word spacing within one label/value.
SEGMENT_GAP_HEIGHT_RATIO = 3.5

# A vertical gap to the next line larger than this multiple of line height
# implies a large blank region below a label (a multiline text area) rather
# than a normal single-line follow-up.
LARGE_VERTICAL_GAP_RATIO = 2.5

# A heading and the option line directly below it must be within this
# multiple of line height to be considered part of the same choice group.
CLOSE_BELOW_RATIO = 2.5


def right_edge(box: BoundingBox) -> float:
    return box.x + box.width


def bottom_edge(box: BoundingBox) -> float:
    return box.y + box.height


def vertical_center(box: BoundingBox) -> float:
    return box.y + box.height / 2


def vertically_overlaps(a: BoundingBox, b: BoundingBox, tolerance: float) -> bool:
    center_gap = abs(vertical_center(a) - vertical_center(b))
    return center_gap <= tolerance * max(a.height, b.height, 1.0)


def horizontally_overlaps(a: BoundingBox, b: BoundingBox) -> bool:
    return a.x < right_edge(b) and b.x < right_edge(a)


def is_left_of(label: BoundingBox, target: BoundingBox, max_gap: float) -> bool:
    """True if `label` sits on the same line, immediately to the left of `target`."""
    if not vertically_overlaps(label, target, _LINE_CLUSTER_TOLERANCE):
        return False
    gap = target.x - right_edge(label)
    return 0 <= gap <= max_gap


def is_above(label: BoundingBox, target: BoundingBox, max_gap: float) -> bool:
    """True if `label` sits directly above `target`, with overlapping columns."""
    if not horizontally_overlaps(label, target):
        return False
    gap = target.y - bottom_edge(label)
    return 0 <= gap <= max_gap


def is_close_below(
    upper: BoundingBox, lower: BoundingBox, max_gap_ratio: float = CLOSE_BELOW_RATIO
) -> bool:
    """True if `lower` sits directly below `upper` within a small vertical
    gap relative to line height (used to attach an options line to its
    heading)."""
    gap = lower.y - bottom_edge(upper)
    if gap < 0:
        return False
    threshold = max_gap_ratio * max(upper.height, lower.height, 1.0)
    return gap <= threshold


def is_large_vertical_gap(
    upper: BoundingBox,
    lower: BoundingBox,
    min_gap_ratio: float = LARGE_VERTICAL_GAP_RATIO,
) -> bool:
    """True if the vertical gap between `upper` and `lower` is large relative
    to line height (used to infer a blank multiline area below a label)."""
    gap = lower.y - bottom_edge(upper)
    threshold = min_gap_ratio * max(upper.height, lower.height, 1.0)
    return gap > threshold


def union_bounding_box(boxes: list[BoundingBox]) -> BoundingBox:
    min_x = min(b.x for b in boxes)
    min_y = min(b.y for b in boxes)
    max_x = max(right_edge(b) for b in boxes)
    max_y = max(bottom_edge(b) for b in boxes)
    return BoundingBox(x=min_x, y=min_y, width=max_x - min_x, height=max_y - min_y)


def group_tokens_into_lines(
    tokens: tuple[DetectionToken, ...],
) -> list[list[DetectionToken]]:
    """Clusters tokens into visual lines by vertical proximity, then orders
    each line left-to-right. Order of lines follows reading order
    (top-to-bottom, then left-to-right for ties).
    """
    remaining = sorted(tokens, key=lambda t: (t.bounding_box.y, t.bounding_box.x))
    lines: list[list[DetectionToken]] = []

    for token in remaining:
        placed = False
        for line in lines:
            if vertically_overlaps(
                line[0].bounding_box, token.bounding_box, _LINE_CLUSTER_TOLERANCE
            ):
                line.append(token)
                placed = True
                break
        if not placed:
            lines.append([token])

    for line in lines:
        line.sort(key=lambda t: t.bounding_box.x)

    lines.sort(key=lambda line: (line[0].bounding_box.y, line[0].bounding_box.x))
    return lines


def split_line_into_segments(
    tokens: list[DetectionToken], gap_height_ratio: float = SEGMENT_GAP_HEIGHT_RATIO
) -> list[list[DetectionToken]]:
    """Splits tokens already on one visual line into segments wherever the
    horizontal gap between consecutive tokens is large relative to token
    height. A normal label like "Full Name: John" stays one segment (only
    single-space gaps); two labels sharing one line like "Signature:" and
    "Date:" — separated by blank input space with nothing drawn between
    them — split into separate segments.
    """
    if not tokens:
        return []

    ordered = sorted(tokens, key=lambda t: t.bounding_box.x)
    segments: list[list[DetectionToken]] = [[ordered[0]]]

    for token in ordered[1:]:
        previous = segments[-1][-1]
        gap = token.bounding_box.x - right_edge(previous.bounding_box)
        threshold = gap_height_ratio * max(
            previous.bounding_box.height, token.bounding_box.height, 1.0
        )
        if gap > threshold:
            segments.append([token])
        else:
            segments[-1].append(token)

    return segments
