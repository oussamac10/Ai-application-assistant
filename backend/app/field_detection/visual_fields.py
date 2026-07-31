"""Finding text fields in a flattened PDF, where nothing marks them but ink.

A form with AcroForm widgets tells you where its fields are. A flattened one —
printed, scanned, or exported without interactivity — tells you nothing: an
underline beneath a label and a box beside one are just drawings, identical to
the rule under a heading or the border of a table.

The local pass previously read only choice groups on such documents. On the
committed French form that meant 8 candidates against 17 label lines, which is
correct behaviour from coverage's point of view (it escalates) but wrong from
the user's: the hybrid safety net ends up paying for work local extraction
should be doing.

The rule is geometric and has no vocabulary in it:

    Nom de famille *          <- a short label
    ______________________    <- a drawn region directly beneath it

A drawn region is an input area when a plausible label sits beside or above it.
Everything else about the approach is about *not* creating fields:
decorative rules under headings, table borders, separators between sections and
the line under a document title all have the same shape as a real underline, and
the only thing distinguishing them is what is written near them.

So association is deliberately strict, and where it cannot find a short,
concise, non-prose label the region produces no field at all. A missing question
is recoverable — the user can still fill the printed form — while an invented
one asks somebody for something the document never requested.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from app.field_detection.providers.base import (
    BoundingBox,
    DetectionPageInput,
    DetectionToken,
    RuledRegion,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Thresholds. Documented and configurable rather than tuned to one document —
# every one is expressed against the page or the region, not in absolute points
# taken from a fixture.
# ---------------------------------------------------------------------------

# A usable input region is at least this wide. Below it there is nowhere to
# write, and short rules are usually decoration.
MIN_REGION_WIDTH = 60.0

# How far below a label its underline may sit, as a multiple of the label's own
# text height. Beyond this they are unrelated things that happen to be near.
MAX_LABEL_GAP_RATIO = 2.2

# A box taller than this many points holds more than one line of writing.
MULTILINE_HEIGHT = 34.0

# A label is short. This is the single most important filter: a legal
# paragraph, an instruction and a document title are all long, and all of them
# sit above rules that look exactly like input underlines.
MAX_LABEL_WORDS = 9
MIN_LABEL_CHARACTERS = 2

# A region within this fraction of the page edge is a border or a footer rule.
# 6% of A4 is about 50pt — a genuine page margin. A form does not put an input
# closer to the edge than that, while page-number rules and borders live there.
PAGE_MARGIN_RATIO = 0.06

# A region spanning this much of the page width is a separator, not a field.
# A form's inputs sit inside its margins and columns; a rule that runs almost
# edge to edge is dividing the page. The committed French form draws exactly
# this under each page title, and its subtitle sits above it looking enough
# like a label to be mistaken for one.
MAX_REGION_WIDTH_RATIO = 0.85

# How far left of a region its inline label may start, as a multiple of the
# region height. Keeps "Name: ____" together and rejects a label from the
# previous column.
MAX_INLINE_LABEL_DISTANCE_RATIO = 4.0


@dataclass(frozen=True)
class VisualField:
    """One detected blank region and the label that names it."""

    label: str
    field_type: str
    page_number: int
    label_bounding_box: BoundingBox | None
    input_bounding_box: BoundingBox
    confidence: float
    review_required: bool
    association: str  # how the label was found — for diagnostics and review


@dataclass(frozen=True)
class VisualCounts:
    """Counts only. No label, coordinate or document text ever leaves here."""

    underlines: int = 0
    boxes: int = 0
    multiline_boxes: int = 0
    label_pairs: int = 0
    text_fields: int = 0
    multiline_fields: int = 0
    filtered: int = 0
    ambiguous: int = 0


# Prose markers. A line ending in a full stop is a sentence; one ending in a
# colon is asking for something.
_SENTENCE_END = re.compile(r"[.!?]\s*$")
_TRAILING_COLON = re.compile(r"[:：]\s*$")
_PLACEHOLDER = re.compile(r"^[\W\d_]*$", re.UNICODE)


def is_plausible_label(text: str) -> bool:
    """Whether a line could be naming an input.

    Punctuation and length only. A heading, a legal paragraph and an
    instruction are all rejected for being long or for reading as sentences —
    never for containing a particular word, so the rule behaves the same in
    French, German and Arabic.
    """
    stripped = text.strip()
    if len(stripped) < MIN_LABEL_CHARACTERS:
        return False
    if _PLACEHOLDER.match(stripped):
        return False
    words = stripped.split()
    if len(words) > MAX_LABEL_WORDS:
        return False
    # A full sentence is prose. A colon at the end is the opposite — it is a
    # form asking a question — so it survives even if it ends in punctuation.
    if _SENTENCE_END.search(stripped) and not _TRAILING_COLON.search(stripped):
        return False
    return True


def _line_of(
    token: DetectionToken, tokens: list[DetectionToken]
) -> list[DetectionToken]:
    box = token.bounding_box
    centre = box.y + box.height / 2
    return sorted(
        (
            other
            for other in tokens
            if abs(other.bounding_box.y + other.bounding_box.height / 2 - centre)
            <= max(box.height, other.bounding_box.height) * 0.6
        ),
        key=lambda t: t.bounding_box.x,
    )


def _text_of(line: list[DetectionToken]) -> str:
    return " ".join(token.text for token in line).strip()


def _region_is_decorative(region: RuledRegion, page: DetectionPageInput) -> bool:
    """Whether a drawn region is furniture rather than an input area."""
    box = region.bounding_box
    if box.width < MIN_REGION_WIDTH:
        return True
    if page.width and box.width / page.width > MAX_REGION_WIDTH_RATIO:
        # A rule spanning almost the whole page separates sections.
        return True
    if page.height:
        margin = page.height * PAGE_MARGIN_RATIO
        if box.y < margin or box.y > page.height - margin:
            # A header or footer rule.
            return True
    return False


def _contains_text(region: RuledRegion, tokens: list[DetectionToken]) -> bool:
    """Whether the region already holds writing.

    A box with text in it is a printed cell — a table header, a caption — not
    somewhere the user is being asked to write.
    """
    box = region.bounding_box
    inset = min(box.height * 0.2, 3.0)
    for token in tokens:
        t = token.bounding_box
        centre_x, centre_y = t.x + t.width / 2, t.y + t.height / 2
        if (
            box.x + inset <= centre_x <= box.x + box.width - inset
            and box.y + inset <= centre_y <= box.y + box.height - inset
        ):
            return True
    return False


def _label_beside(
    region: RuledRegion, tokens: list[DetectionToken]
) -> tuple[str, BoundingBox, str] | None:
    """A label on the region's own baseline, to its left ("Name: ______")."""
    box = region.bounding_box
    centre = box.y + box.height / 2
    height = max(box.height, 10.0)
    candidates = [
        token
        for token in tokens
        if token.bounding_box.x + token.bounding_box.width <= box.x + 2
        and box.x - (token.bounding_box.x + token.bounding_box.width)
        < height * MAX_INLINE_LABEL_DISTANCE_RATIO
        and abs(token.bounding_box.y + token.bounding_box.height / 2 - centre)
        <= max(token.bounding_box.height, height) * 0.8
    ]
    if not candidates:
        return None
    line = _line_of(candidates[-1], tokens)
    left = [t for t in line if t.bounding_box.x < box.x]
    text = _text_of(left)
    if not is_plausible_label(text):
        return None
    return text, _union([t.bounding_box for t in left]), "same_row"


def _label_above(
    region: RuledRegion, tokens: list[DetectionToken]
) -> tuple[str, BoundingBox, str] | None:
    """A label directly above the region, within its own horizontal span.

    The dominant pattern in real forms: a caption over a ruled line. The
    horizontal overlap requirement is what keeps a two-column layout's columns
    apart — the label above the left column never claims the right one's rule.
    """
    box = region.bounding_box
    above = [
        token
        for token in tokens
        if token.bounding_box.y + token.bounding_box.height <= box.y + 2
        and token.bounding_box.x + token.bounding_box.width > box.x
        and token.bounding_box.x < box.x + box.width
    ]
    if not above:
        return None

    nearest = max(above, key=lambda t: t.bounding_box.y + t.bounding_box.height)
    gap = box.y - (nearest.bounding_box.y + nearest.bounding_box.height)
    if gap > max(nearest.bounding_box.height, 8.0) * MAX_LABEL_GAP_RATIO:
        return None

    line = [
        token
        for token in _line_of(nearest, tokens)
        # Only the part of the line over this region: a shared line above two
        # columns must not give both of them the same label.
        if token.bounding_box.x + token.bounding_box.width > box.x
        and token.bounding_box.x < box.x + box.width
    ]
    text = _text_of(line)
    if not is_plausible_label(text):
        return None
    return text, _union([t.bounding_box for t in line]), "above"


def _union(boxes: list[BoundingBox]) -> BoundingBox:
    x0 = min(b.x for b in boxes)
    y0 = min(b.y for b in boxes)
    x1 = max(b.x + b.width for b in boxes)
    y1 = max(b.y + b.height for b in boxes)
    return BoundingBox(x=x0, y=y0, width=x1 - x0, height=y1 - y0)


def detect_visual_fields(
    page: DetectionPageInput,
    claimed_regions: set[tuple[float, float]] | None = None,
) -> tuple[list[VisualField], VisualCounts]:
    """Finds input regions on one page and names them.

    `claimed_regions` are areas another pass already accounted for — a
    signature line, for instance, which is authoritative and must not also
    become a text field.
    """
    claimed = claimed_regions or set()
    tokens = list(page.tokens)
    fields: list[VisualField] = []
    underlines = boxes = multiline = filtered = ambiguous = pairs = 0

    for region in page.ruled_regions:
        if region.kind == "underline":
            underlines += 1
        else:
            boxes += 1

        box = region.bounding_box
        if (round(box.x, 1), round(box.y, 1)) in claimed:
            filtered += 1
            continue
        if _region_is_decorative(region, page):
            filtered += 1
            continue
        if region.kind == "box" and _contains_text(region, tokens):
            filtered += 1
            continue

        # Same-row first: "Name: ____" is unambiguous, while a caption above
        # could belong to a neighbouring column.
        found = _label_beside(region, tokens) or _label_above(region, tokens)
        if found is None:
            # No usable label. A missing question is recoverable — the user can
            # still fill the printed form — while an invented one asks for
            # something the document never requested.
            ambiguous += 1
            filtered += 1
            continue

        label, label_box, association = found
        pairs += 1

        is_multiline = box.height >= MULTILINE_HEIGHT
        if is_multiline:
            multiline += 1

        fields.append(
            VisualField(
                label=label,
                field_type="multiline_text" if is_multiline else "text",
                page_number=page.page_number,
                label_bounding_box=label_box,
                input_bounding_box=box,
                # A label on the same row is stronger evidence than one above,
                # which has to be inferred from overlap.
                confidence=0.75 if association == "same_row" else 0.6,
                review_required=association != "same_row",
                association=association,
            )
        )

    counts = VisualCounts(
        underlines=underlines,
        boxes=boxes,
        multiline_boxes=multiline,
        label_pairs=pairs,
        text_fields=sum(1 for f in fields if f.field_type == "text"),
        multiline_fields=sum(1 for f in fields if f.field_type == "multiline_text"),
        filtered=filtered,
        ambiguous=ambiguous,
    )
    _log_counts(counts)
    return fields, counts


def _log_counts(counts: VisualCounts) -> None:
    """Counts only — never a label, a coordinate or any document text."""
    if counts.underlines == 0 and counts.boxes == 0:
        return
    logger.info(
        "Visual field detection: visual_underlines_detected=%d "
        "visual_boxes_detected=%d visual_multiline_boxes_detected=%d "
        "visual_label_region_pairs=%d visual_text_fields_generated=%d "
        "visual_multiline_fields_generated=%d visual_candidates_filtered=%d "
        "visual_ambiguous_candidates=%d",
        counts.underlines,
        counts.boxes,
        counts.multiline_boxes,
        counts.label_pairs,
        counts.text_fields,
        counts.multiline_fields,
        counts.filtered,
        counts.ambiguous,
    )
