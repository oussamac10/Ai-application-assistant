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
