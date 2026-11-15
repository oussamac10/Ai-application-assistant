"""Grouping native AcroForm checkbox widgets into single questions.

The AcroForm path treated every widget as its own field, so a fillable
government form produced one question per checkbox. On the Stuttgart
residence-permit application that is 54 questions where there should be a
dozen: "Ausbildung", "Erwerbstätigkeit", "Familiennachzug" … each asked
separately instead of one "purpose of application"; "ja" and "nein" as two
questions instead of one. And because the widget path bypasses the text-line
passes entirely, none of the visual grouping built earlier in this phase ran on
it at all.

The obvious fix — read `/Kids` and the radio flag — does not work here, and
probably not on most real forms. Every checkbox on this document is an
independent field with `flags=0` and its own name; the author never used native
radio groups. So the grouping evidence has to be geometry, which is what the
*reader* uses too:

    y=95.8  x=67.9   Ausbildung          ┐
    y=110.7 x=67.9   Erwerbstätigkeit    │ same x, regular y steps
    y=124.6 x=67.9   völkerrechtliche…   │ -> one column = one question
    …                                    ┘

    y=374.8 x=67.9   ledig     ┐
    y=374.8 x=114.3  verheiratet│ same y, varying x
    y=374.8 x=237.8  verwitwet  │ -> one row = one question
    …                           ┘

So: widgets that are collinear and regularly spaced belong together, and a gap
that jumps ends the group. No vocabulary, no field-name patterns — the same
rule finds an unanticipated group on an unanticipated form.

Option labels come from the widget's own tooltip (`/TU`, PyMuPDF's
`field_label`), which on this document is already the human text: "Ausbildung",
"ledig", "männlich". That is the spec's first-choice label source and it beats
any geometric guess. The machine name (`chkLedigS1`) is kept separately, because
export has to write back to it.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Callable
from dataclasses import dataclass, field

from app.field_detection.classification import marker_type
from app.field_detection.providers.base import (
    AcroFormWidgetInput,
    BoundingBox,
    DetectionToken,
)

logger = logging.getLogger(__name__)

# Two widgets are on the same row (or in the same column) when their centres
# differ by less than this fraction of a widget's own size. Checkbox widgets on
# a form are uniformly sized, so this is a tight, reliable test.
_ALIGNMENT_TOLERANCE = 0.75

# A gap larger than this multiple of the group's typical spacing ends it. Real
# option lists are evenly spaced; a jump means the next widget belongs to the
# next question. Generous because a long option label pushes the following
# widget further along without starting a new group.
_GAP_BREAK_RATIO = 2.5

# Below two widgets there is no group — a lone checkbox is a boolean.
_MIN_GROUP_SIZE = 2

# A group this large is a checklist rather than a pick-one.
_MAX_EXCLUSIVE_OPTIONS = 8

# Option sets whose members are mutually exclusive by meaning. Used only to
# *raise confidence* in the single/multiple decision — grouping itself never
# consults them, so an unrecognised set still becomes one question.
_EXCLUSIVE_HINTS: tuple[frozenset[str], ...] = (
    frozenset({"ja", "nein"}),
    frozenset({"yes", "no"}),
    frozenset({"oui", "non"}),
    frozenset({"نعم", "لا"}),
    frozenset({"männlich", "weiblich", "divers"}),
    frozenset({"male", "female"}),
    frozenset(
        {
            "ledig",
            "verheiratet",
            "lebenspartnerschaft",
            "verwitwet",
            "geschieden",
            "getrennt lebend",
        }
    ),
    frozenset({"single", "married", "widowed", "divorced", "separated"}),
)

# Machine-generated widget names that carry no meaning for a user.
_MACHINE_NAME = re.compile(
    r"^(?:chk|cb|check\s*box|checkbox|field|group|opt|radio|btn)[\s_\-]*[0-9a-z]*$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class WidgetOption:
    """One checkbox inside a group, with everything export needs later."""

    label: str
    # The AcroForm field name. Never shown to a user; kept because filling the
    # form means writing back to this exact widget.
    widget_name: str
    page_number: int
    rect: BoundingBox
    export_value: str | None = None


@dataclass(frozen=True)
class WidgetGroup:
    """A set of checkbox widgets that together ask one question."""

    options: tuple[WidgetOption, ...]
    page_number: int
    orientation: str  # "row" | "column"
    label: str | None = None
    exclusive: bool = False
    review_required: bool = True
    bounding_box: BoundingBox | None = None
    # Identity is (name, page, x, y), not the name alone. Two widgets can share
    # one field name — that is how this form encodes a native ja/nein pair, one
    # field with two differently-valued boxes — so counting names undercounts
    # widgets and made 54 grouped widgets report as "49 claimed, 5 unclaimed".
    claimed_widgets: frozenset[tuple[str, int, float, float]] = field(
        default_factory=frozenset
    )


def is_machine_name(name: str | None) -> bool:
    """Whether a widget name is generated rather than descriptive.

    "Checkbox17" and "chkAzubi" tell a user nothing; a tooltip reading
    "Ausbildung" does. This decides whether to fall back to geometry for a
    label, never whether to keep the name — export always needs it.
    """
    if not name:
        return True
    return bool(_MACHINE_NAME.match(name.strip()))


def _centre(rect: BoundingBox) -> tuple[float, float]:
    return (rect.x + rect.width / 2, rect.y + rect.height / 2)


def _cluster(
    widgets: list[AcroFormWidgetInput], axis: str
) -> list[list[AcroFormWidgetInput]]:
    """Groups widgets that are collinear along `axis` and regularly spaced.

    `axis="row"` means "same y, varying x"; `axis="column"` is the transpose.
    Spacing is compared against the group's own median gap rather than a fixed
    distance, so a densely packed row and a widely spaced column are both read
    correctly without tuning per document.
    """
    if not widgets:
        return []

    same = 1 if axis == "row" else 0  # index of the coordinate that stays put
    vary = 0 if axis == "row" else 1

    buckets: list[list[AcroFormWidgetInput]] = []
    for widget in sorted(
        widgets, key=lambda w: (_centre(w.rect)[same], _centre(w.rect)[vary])
    ):
        centre = _centre(widget.rect)
        size = max(widget.rect.width, widget.rect.height) or 1.0
        placed = False
        for bucket in buckets:
            reference = _centre(bucket[0].rect)
            if abs(centre[same] - reference[same]) <= size * _ALIGNMENT_TOLERANCE:
                bucket.append(widget)
                placed = True
                break
        if not placed:
            buckets.append([widget])

    # Split each collinear run wherever the spacing jumps: evenly spaced options
    # belong to one question, and a wide gap starts the next.
    runs: list[list[AcroFormWidgetInput]] = []
    for bucket in buckets:
        ordered = sorted(bucket, key=lambda w: _centre(w.rect)[vary])
        if len(ordered) < 2:
            runs.append(ordered)
            continue
        gaps = [
            _centre(ordered[i + 1].rect)[vary] - _centre(ordered[i].rect)[vary]
            for i in range(len(ordered) - 1)
        ]
        typical = sorted(gaps)[len(gaps) // 2] or 1.0
        current = [ordered[0]]
        for widget, gap in zip(ordered[1:], gaps, strict=True):
            if gap > typical * _GAP_BREAK_RATIO:
                runs.append(current)
                current = [widget]
            else:
                current.append(widget)
        runs.append(current)
    return runs


# A wrapped option list continues on the next line. Merged only when the rows
# are this close vertically (as a multiple of widget height) — far enough apart
# and they are two questions that happen to sit near each other.
_WRAP_MAX_ROW_GAP = 1.6


def _merge_wrapped_rows(
    runs: list[list[AcroFormWidgetInput]],
    tokens: tuple[DetectionToken, ...] = (),
    row_lookup: RowLookup | None = None,
) -> list[list[AcroFormWidgetInput]]:
    """Joins an option list that wrapped onto a following row.

    "Zweck des Aufenthalts" offers six options laid out three-and-three:

        [_] Sprachkurs  [_] Studium     [_] Arbeitsaufnahme
        [_] Werkvertrag [_] Au-Pair     [_] Sonstiges

    Row clustering sees two rows and produces two questions. The evidence that
    they are one: the rows are vertically adjacent, start at the same x, and
    use identically sized widgets — a continuation, not a neighbour.

    Deliberately conservative. Two genuinely different questions stacked
    closely (the legal ja/nein rows) start at *different* x positions and stay
    separate, and a merge is only ever attempted between immediately
    consecutive rows.
    """
    if len(runs) < 2:
        return runs

    ordered = sorted(runs, key=lambda run: min(_centre(w.rect)[1] for w in run))
    merged: list[list[AcroFormWidgetInput]] = [ordered[0]]

    for run in ordered[1:]:
        previous = merged[-1]
        if (
            _is_wrapped_continuation(previous, run)
            and not _text_between(previous, run, tokens)
            and not _different_table_rows(previous, run, row_lookup)
        ):
            merged[-1] = previous + run
        else:
            merged.append(run)
    return merged


def _different_table_rows(
    previous: list[AcroFormWidgetInput],
    run: list[AcroFormWidgetInput],
    row_lookup: RowLookup | None,
) -> bool:
    """Whether two runs sit in different rows of a repeated table.

    Decisive where nothing else is. Each child's gender pair is a separate
    question about a separate person, but the pairs share a left edge, a widget
    size and a spacing, and the cells between them are *widgets* rather than
    text — so every other guard says "wrapped continuation" and all six rows
    merged into one twelve-option group.
    """
    if row_lookup is None:
        return False
    previous_rows = {row_lookup(w.field_name) for w in previous} - {None}
    run_rows = {row_lookup(w.field_name) for w in run} - {None}
    if not previous_rows or not run_rows:
        return False
    return previous_rows != run_rows


def _text_between(
    previous: list[AcroFormWidgetInput],
    run: list[AcroFormWidgetInput],
    tokens: tuple[DetectionToken, ...],
) -> bool:
    """Whether a new question is written between two option rows.

    This is the decisive signal, and geometry alone is not enough: on the
    reference form "Wie sind Sie untergebracht?" and "Zweck des Aufenthalts"
    sit in adjacent, identically aligned rows of identically sized widgets, so
    every positional test says "continuation". What separates them is that the
    second question's *text* is printed between the two rows — and a genuinely
    wrapped list has nothing between its lines but the options themselves.

    Only text starting to the left of the options counts. The option labels
    themselves sit beside their widgets and must not be mistaken for a new
    question.
    """
    if not tokens:
        return False
    previous_bottom = max(w.rect.y + w.rect.height for w in previous)
    run_top = min(w.rect.y for w in run)
    left_edge = min(w.rect.x for w in previous)

    return any(
        previous_bottom <= token.bounding_box.y < run_top
        and token.bounding_box.x < left_edge - 1
        for token in tokens
    )


def _is_wrapped_continuation(
    previous: list[AcroFormWidgetInput], run: list[AcroFormWidgetInput]
) -> bool:
    if not previous or not run or len(previous) < 2 or len(run) < 2:
        return False

    previous_bottom = max(w.rect.y + w.rect.height for w in previous)
    run_top = min(w.rect.y for w in run)
    height = max(w.rect.height for w in previous) or 1.0
    if not (-height <= run_top - previous_bottom <= height * _WRAP_MAX_ROW_GAP):
        return False

    # Same left edge: a continuation restarts the list, a different question
    # starts wherever its own text ended.
    left_previous = min(w.rect.x for w in previous)
    left_run = min(w.rect.x for w in run)
    if abs(left_previous - left_run) > height:
        return False

    # Same widget size — a different control size means a different purpose.
    if abs(previous[0].rect.width - run[0].rect.width) > 1.0:
        return False

    # Native evidence outranks geometry: when each row's widgets carry their
    # own shared tooltip and the two differ, the author labelled them as two
    # questions. The reference form's consecutive legal rows are exactly this
    # ("polizeiliches Ermittlungsverfahren" then "Strafbefehl erlassen"), and
    # they align too well for any positional test to separate them.
    previous_tooltip = _shared_tooltip(previous)
    run_tooltip = _shared_tooltip(run)
    if previous_tooltip and run_tooltip and previous_tooltip != run_tooltip:
        return False

    return True


def _shared_tooltip(run: list[AcroFormWidgetInput]) -> str | None:
    """The tooltip every widget in a run carries, when they all agree."""
    labels = {(w.field_label or "").strip() for w in run}
    if len(labels) == 1:
        only = next(iter(labels))
        return only or None
    return None


# Generic checkbox-value / action tooltips that PDF authors repeat on every
# checkbox widget (e.g. /TU = "ja"). These describe checking the box, not the
# question being asked, so they must never shadow the real heading above/left.
_GENERIC_CHECKBOX_TOOLTIPS = frozenset(
    {
        "ja",
        "nein",
        "yes",
        "no",
        "oui",
        "non",
        "si",
        "sí",
        "true",
        "false",
        "on",
        "off",
        "1",
        "0",
        "x",
        "✓",
        "✔",
        "check",
        "checked",
        "checkbox",
        "auswählen",
        "ankreuzen",
        "bitte ankreuzen",
        "select",
        "auswahl",
    }
)


def _is_generic_checkbox_tooltip(text: str) -> bool:
    return text.strip().lower() in _GENERIC_CHECKBOX_TOOLTIPS


def _nearest_label_left(
    box: BoundingBox, tokens: tuple[DetectionToken, ...]
) -> str | None:
    """The question text immediately to the left of a horizontal checkbox row."""
    if not tokens:
        return None
    # Align with the top/first row of the group box (usually ~12-16pt tall).
    row_center_y = box.y + min(box.height, 20.0) / 2.0
    tolerance = max(min(box.height, 20.0) * 0.65, 8.0)

    same_row_left = [
        token
        for token in tokens
        if abs((token.bounding_box.y + token.bounding_box.height / 2.0) - row_center_y)
        <= tolerance
        and token.bounding_box.x + token.bounding_box.width <= box.x + 1.0
        and marker_type(token.text) is None
    ]
    if not same_row_left:
        return None

    ordered = sorted(
        same_row_left,
        key=lambda t: t.bounding_box.x + t.bounding_box.width,
        reverse=True,
    )
    nearest = ordered[0]
    if box.x - (nearest.bounding_box.x + nearest.bounding_box.width) > 35.0:
        return None

    # Stop at any marker token on the same baseline (e.g. a preceding
    # "[_] ja [_] nein" group to the left on the same row).
    markers_left = [
        token.bounding_box.x + token.bounding_box.width
        for token in tokens
        if abs((token.bounding_box.y + token.bounding_box.height / 2.0) - row_center_y)
        <= tolerance
        and token.bounding_box.x + token.bounding_box.width <= nearest.bounding_box.x
        and marker_type(token.text) is not None
    ]
    marker_barrier_x = max(markers_left, default=float("-inf"))

    collected = [nearest]
    cursor_left = nearest.bounding_box.x
    for token in ordered[1:]:
        right = token.bounding_box.x + token.bounding_box.width
        if right <= marker_barrier_x + 1.0:
            break
        if cursor_left - right > 16.0:
            break
        collected.append(token)
        cursor_left = token.bounding_box.x

    # If a marker barrier stopped us right after a previous option's label
    # (e.g. "[_] nein  Bad/Dusche?"), we already stopped at marker_barrier_x,
    # wait — "nein" is to the *right* of "[_]"! Check if there is a wide gap
    # or if the leftmost collected word sits right next to a marker.
    collected.reverse()
    # If a marker barrier stopped us right after a previous option's short
    # label (e.g. "[_] nein  Nutzung Bad/Dusche?"), drop that leading option
    # token so it does not bleed into the next question.
    if (
        len(collected) >= 2
        and marker_barrier_x > float("-inf")
        and collected[0].bounding_box.x - marker_barrier_x <= 10.0
        and collected[0].text.strip().lower()
        in {"ja", "nein", "yes", "no", "oui", "non", "x"}
    ):
        collected = collected[1:]
    text = " ".join(
        token.text.strip() for token in collected if token.text.strip()
    ).strip()
    if not text or not any(ch.isalpha() for ch in text):
        return None
    return text


def _nearest_label_above(
    box: BoundingBox, tokens: tuple[DetectionToken, ...]
) -> str | None:
    """The text line closest above the group, which is its question.

    Deliberately simple and deliberately conservative: a wrong group *name* is
    a cosmetic problem, while a wrong group is a broken form. When nothing
    plausible sits above, the group keeps no label and is flagged for review
    rather than being given an invented one.
    """
    candidates = [
        token
        for token in tokens
        if token.bounding_box.y + token.bounding_box.height <= box.y + 2
        and box.y - (token.bounding_box.y + token.bounding_box.height) < 40
    ]
    if not candidates:
        return None
    highest = max(candidates, key=lambda t: t.bounding_box.y + t.bounding_box.height)
    baseline = highest.bounding_box.y
    line = [
        token
        for token in candidates
        if abs(token.bounding_box.y - baseline) <= token.bounding_box.height
    ]
    text = " ".join(
        token.text for token in sorted(line, key=lambda t: t.bounding_box.x)
    ).strip()
    return text or None


# An option label sits on the widget's own baseline. This is a fraction of the
# widget height rather than a fixed distance, because it has to hold for a
# 9pt checkbox and a 20pt one alike.
_SAME_BASELINE_TOLERANCE = 0.45

# How far beside a widget its label can start. Beyond this the nearest text
# belongs to something else.
_LABEL_SEARCH_DISTANCE = 70.0

# An option is a short phrase. A long word run beside a checkbox is the
# question, or prose, or the next column — never the answer.
_MAX_OPTION_LABEL_WORDS = 5


def _join_wrapped_option_lines(line1: str, line2: str) -> str:
    if line1.endswith("-") and line2 and line2[0].islower():
        return f"{line1[:-1]}{line2}"
    return f"{line1} {line2}"


def _label_beside(
    rect: BoundingBox,
    tokens: tuple[DetectionToken, ...],
    *,
    rtl: bool = False,
    stop_x: float | None = None,
    other_widget_rects: tuple[BoundingBox, ...] = (),
) -> str | None:
    """The option text belonging to one widget.

    Used when a group's widgets all share a tooltip, so the distinguishing text
    exists only on the page. Getting it wrong is subtle and damaging: the
    reference form's "Ausweisung" row put `Bundesrepublik` — a word from the
    *question*, printed on the line above — 0.2pt to the left of `nein`, and a
    nearest-by-x search picked it.

    So vertical agreement is decided first and strictly. A label shares the
    widget's baseline; anything on another line is a different sentence,
    however close it looks horizontally. Only among true same-baseline tokens
    does horizontal distance break the tie.
    """
    centre_y = rect.y + rect.height / 2
    tolerance = rect.height * _SAME_BASELINE_TOLERANCE

    def on_baseline(token: DetectionToken) -> bool:
        box = token.bounding_box
        return abs(box.y + box.height / 2 - centre_y) <= tolerance

    # Reading direction decides which side to look at: an RTL form puts the
    # label to the widget's left.
    if rtl:

        def beside(token: DetectionToken) -> bool:
            box = token.bounding_box
            if stop_x is not None and box.x + box.width <= stop_x + 1:
                return False
            return (
                box.x + box.width <= rect.x + 1
                and rect.x - (box.x + box.width) < _LABEL_SEARCH_DISTANCE
            )

        def distance(token: DetectionToken) -> float:
            return rect.x - (token.bounding_box.x + token.bounding_box.width)
    else:

        def beside(token: DetectionToken) -> bool:
            box = token.bounding_box
            if stop_x is not None and box.x >= stop_x - 1:
                return False
            return (
                box.x >= rect.x + rect.width - 1
                and box.x - (rect.x + rect.width) < _LABEL_SEARCH_DISTANCE
            )

        def distance(token: DetectionToken) -> float:
            return token.bounding_box.x - (rect.x + rect.width)

    candidates = [
        t
        for t in tokens
        if on_baseline(t) and beside(t) and marker_type(t.text) is None
    ]
    if not candidates:
        return None

    nearest = min(candidates, key=distance)
    max_token_gap = max(rect.height * 0.9, 10.0)

    # Collect consecutive same-baseline words forming one option phrase
    # (e.g. "getrennt" + "lebend"), stopping at markers, the next widget, or a gap.
    line_tokens = [nearest]
    if rtl:
        rest = sorted(
            (
                t
                for t in tokens
                if on_baseline(t)
                and t is not nearest
                and t.bounding_box.x + t.bounding_box.width
                <= nearest.bounding_box.x + 1
                and (
                    stop_x is None
                    or t.bounding_box.x + t.bounding_box.width > stop_x + 1
                )
            ),
            key=lambda t: t.bounding_box.x + t.bounding_box.width,
            reverse=True,
        )
        edge = nearest.bounding_box.x
        for tok in rest:
            if marker_type(tok.text) is not None:
                break
            gap = edge - (tok.bounding_box.x + tok.bounding_box.width)
            if gap > max_token_gap:
                break
            line_tokens.append(tok)
            edge = tok.bounding_box.x
        line_tokens.reverse()
    else:
        rest = sorted(
            (
                t
                for t in tokens
                if on_baseline(t)
                and t is not nearest
                and t.bounding_box.x
                >= nearest.bounding_box.x + nearest.bounding_box.width - 1
                and (stop_x is None or t.bounding_box.x < stop_x - 1)
            ),
            key=lambda t: t.bounding_box.x,
        )
        edge = nearest.bounding_box.x + nearest.bounding_box.width
        for tok in rest:
            if marker_type(tok.text) is not None:
                break
            gap = tok.bounding_box.x - edge
            if gap > max_token_gap:
                break
            line_tokens.append(tok)
            edge = tok.bounding_box.x + tok.bounding_box.width

    text = " ".join(t.text.strip() for t in line_tokens if t.text.strip()).strip()
    if not text or len(text.split()) > _MAX_OPTION_LABEL_WORDS:
        return None

    # Check for a wrapped continuation line directly beneath the first line
    # (e.g. "Aufenthalts-" / "erlaubnis" or "sonstiger" / "Status").
    line1_bottom = max(t.bounding_box.y + t.bounding_box.height for t in line_tokens)
    line1_height = max(t.bounding_box.height for t in line_tokens) or 9.0
    line1_x = line_tokens[0].bounding_box.x
    below_candidates = [
        t
        for t in tokens
        if marker_type(t.text) is None
        and 0.0 <= t.bounding_box.y - line1_bottom <= line1_height * 0.85
        and abs(t.bounding_box.x - line1_x) <= 8.0
        and (stop_x is None or t.bounding_box.x < stop_x - 1)
    ]
    if below_candidates:
        first_below = min(below_candidates, key=lambda t: t.bounding_box.x)
        below_center_y = (
            first_below.bounding_box.y + first_below.bounding_box.height / 2
        )
        # Never swallow a token that sits on another checkbox widget's baseline
        # (e.g. consecutive tightly-spaced yes/no rows).
        belongs_to_other_widget = any(
            abs((w_rect.y + w_rect.height / 2) - below_center_y)
            <= w_rect.height * _SAME_BASELINE_TOLERANCE
            and w_rect is not rect
            and w_rect.y > rect.y + rect.height * 0.5
            for w_rect in other_widget_rects
        )
        if not belongs_to_other_widget:
            below_line = [first_below]
            below_edge = first_below.bounding_box.x + first_below.bounding_box.width
            for tok in sorted(
                (
                    t
                    for t in tokens
                    if t is not first_below
                    and marker_type(t.text) is None
                    and abs(t.bounding_box.y - first_below.bounding_box.y)
                    <= first_below.bounding_box.height * 0.5
                    and t.bounding_box.x >= below_edge - 1
                    and (stop_x is None or t.bounding_box.x < stop_x - 1)
                ),
                key=lambda t: t.bounding_box.x,
            ):
                if tok.bounding_box.x - below_edge > max_token_gap:
                    break
                below_line.append(tok)
                below_edge = tok.bounding_box.x + tok.bounding_box.width
            line2_text = " ".join(
                t.text.strip() for t in below_line if t.text.strip()
            ).strip()
            if line2_text:
                joined = _join_wrapped_option_lines(text, line2_text)
                if len(joined.split()) <= _MAX_OPTION_LABEL_WORDS:
                    text = joined

    return text


def _next_widget_stop_x(
    option: WidgetOption, options: tuple[WidgetOption, ...]
) -> float | None:
    rect = option.rect
    centre_y = rect.y + rect.height / 2
    tolerance = rect.height * _SAME_BASELINE_TOLERANCE
    right_neighbours = [
        other.rect.x
        for other in options
        if other is not option
        and abs((other.rect.y + other.rect.height / 2) - centre_y) <= tolerance
        and other.rect.x > rect.x + rect.width
    ]
    return min(right_neighbours) if right_neighbours else None


def _resolve_option_labels(
    options: tuple[WidgetOption, ...],
    tokens: tuple[DetectionToken, ...],
    other_widget_rects: tuple[BoundingBox, ...] = (),
) -> tuple[tuple[WidgetOption, ...], str | None]:
    """Returns (options, shared_tooltip_used_as_question).

    When every widget in a group carries the same tooltip, that text is the
    question (unless it is a generic checkbox value like "ja"/"yes") and
    cannot also be the answers. Each option's own label is then read from the
    page immediately to its right; if that fails the group is left alone,
    because two identically-labelled options are worse than one unlabelled
    group.
    """
    labels = {option.label for option in options}
    if len(labels) != 1:
        return options, None

    shared = next(iter(labels))
    rewritten: list[WidgetOption] = []
    for option in options:
        text = _label_beside(
            option.rect,
            tokens,
            stop_x=_next_widget_stop_x(option, options),
            other_widget_rects=other_widget_rects,
        )
        if not text:
            return options, None
        rewritten.append(
            WidgetOption(
                label=text,
                widget_name=option.widget_name,
                page_number=option.page_number,
                rect=option.rect,
                export_value=option.export_value,
            )
        )
    effective_question = None if _is_generic_checkbox_tooltip(shared) else shared
    return tuple(rewritten), effective_question


# Resolves a widget name to (section key, 1-based row index), or None. Injected
# so this module never imports the repeated-row detector, keeping the two
# independent.
RowLookup = Callable[[str], tuple[str, int] | None]


def _row_scoped_label(
    run: list[AcroFormWidgetInput],
    options: tuple[WidgetOption, ...],
    row_lookup: RowLookup | None,
) -> str | None:
    """A row-specific question for a group inside a repeated table row.

    "Gender — Child 2" rather than the table header repeated once per child.
    The option text names the question (the widgets themselves are labelled
    "männlich"/"weiblich"), and the row index says which row it belongs to —
    both facts the document supplies, so nothing is invented.
    """
    if row_lookup is None:
        return None
    located = {row_lookup(widget.field_name) for widget in run}
    located.discard(None)
    # Every widget must agree, or this is not one row's group.
    if len(located) != 1:
        return None
    section_key, row_index = next(iter(located))  # type: ignore[misc]
    descriptor = " / ".join(option.label for option in options)
    return f"{descriptor} — {section_key} {row_index}"


def _looks_exclusive(labels: tuple[str, ...]) -> bool:
    """Whether picking more than one of these makes sense.

    Only ever *raises* confidence: an unrecognised set stays a group either
    way, it is simply reported as ambiguous so a reviewer can decide.
    """
    normalized = {label.strip().lower() for label in labels}
    if len(normalized) > _MAX_EXCLUSIVE_OPTIONS:
        return False
    return any(normalized <= hint or hint <= normalized for hint in _EXCLUSIVE_HINTS)


def group_checkbox_widgets(
    widgets: list[AcroFormWidgetInput],
    tokens_by_page: dict[int, tuple[DetectionToken, ...]] | None = None,
    row_lookup: RowLookup | None = None,
) -> list[WidgetGroup]:
    """Clusters checkbox widgets into questions, page by page.

    Row clustering is tried first and column clustering fills in what it could
    not claim, because a row of options is the more common layout and a column
    of *single* checkboxes (each its own consent) must not be swept into one
    question by an over-eager column rule.
    """
    tokens_by_page = tokens_by_page or {}
    groups: list[WidgetGroup] = []

    by_page: dict[int, list[AcroFormWidgetInput]] = {}
    for widget in widgets:
        if widget.field_type != "checkbox":
            continue
        by_page.setdefault(widget.page_number, []).append(widget)

    for page_number, page_widgets in sorted(by_page.items()):
        claimed: set[tuple[str, int, float, float]] = set()
        page_tokens = tokens_by_page.get(page_number, ())

        for orientation in ("row", "column"):
            remaining = [w for w in page_widgets if widget_identity(w) not in claimed]
            runs = _cluster(remaining, orientation)
            if orientation == "row":
                # An option list that wrapped onto the next row is one question.
                runs = _merge_wrapped_rows(runs, page_tokens, row_lookup)
            for run in runs:
                if len(run) < _MIN_GROUP_SIZE:
                    continue
                options = tuple(
                    WidgetOption(
                        # The tooltip is the human text on this document, and
                        # the spec's first-choice label source. Falling back to
                        # the machine name would show "chkLedigS1" to a user.
                        label=(w.field_label or w.field_name or "").strip(),
                        widget_name=w.field_name,
                        page_number=w.page_number,
                        rect=w.rect,
                        export_value=w.export_value,
                    )
                    for w in run
                )
                if any(not option.label for option in options):
                    continue

                # A tooltip repeated across every widget is the question, not
                # the answers.
                options, shared_question = _resolve_option_labels(
                    options,
                    page_tokens,
                    tuple(w.rect for w in page_widgets),
                )

                box = _union([w.rect for w in run])
                labels = tuple(option.label for option in options)

                # A group inside a repeated table row belongs to *that* row.
                # Without this every child's gender question was the table
                # header, so all four read identically and none of them said
                # which child it was about.
                row_label = _row_scoped_label(run, options, row_lookup)
                exclusive = _looks_exclusive(labels)
                groups.append(
                    WidgetGroup(
                        options=options,
                        page_number=page_number,
                        orientation=orientation,
                        # The author's own tooltip beats any geometric guess.
                        label=(
                            row_label
                            or shared_question
                            or (
                                _nearest_label_left(box, page_tokens)
                                if orientation == "row"
                                else None
                            )
                            or _nearest_label_above(box, page_tokens)
                        ),
                        exclusive=exclusive,
                        # Anything the exclusivity hints did not recognise is
                        # kept as a group but marked for a human to confirm the
                        # single/multiple decision. Preserving the group and
                        # admitting uncertainty beats emitting N text questions.
                        review_required=not exclusive,
                        bounding_box=box,
                        claimed_widgets=frozenset(widget_identity(w) for w in run),
                    )
                )
                claimed.update(widget_identity(w) for w in run)

    _log_counts(widgets, groups)
    return groups


def _union(boxes: list[BoundingBox]) -> BoundingBox:
    x0 = min(b.x for b in boxes)
    y0 = min(b.y for b in boxes)
    x1 = max(b.x + b.width for b in boxes)
    y1 = max(b.y + b.height for b in boxes)
    return BoundingBox(x=x0, y=y0, width=x1 - x0, height=y1 - y0)


def widget_identity(widget: AcroFormWidgetInput) -> tuple[str, int, float, float]:
    """A widget's identity for claim tracking.

    The field *name* is not unique: this form gives both boxes of a ja/nein
    question the same name, distinguishing them only by export value and
    position. Position completes the identity.
    """
    return (widget.field_name, widget.page_number, widget.rect.x, widget.rect.y)


def claimed_widgets(groups: list[WidgetGroup]) -> set[tuple[str, int, float, float]]:
    """Every widget already accounted for by a group.

    The AcroForm pass skips these so a grouped checkbox is never *also* emitted
    as its own question.
    """
    return {identity for group in groups for identity in group.claimed_widgets}


def _log_counts(widgets: list[AcroFormWidgetInput], groups: list[WidgetGroup]) -> None:
    """Counts only — never a widget name, tooltip or user value, any of which
    can carry document content."""
    checkboxes = [w for w in widgets if w.field_type == "checkbox"]
    claimed = claimed_widgets(groups)
    logger.info(
        "AcroForm widget grouping: acroform_widgets_total=%d "
        "acroform_text_widgets=%d acroform_checkbox_widgets=%d "
        "acroform_groups_created=%d acroform_exclusive_groups=%d "
        "acroform_ambiguous_groups=%d acroform_widgets_claimed=%d "
        "acroform_widgets_unclaimed=%d",
        len(widgets),
        sum(1 for w in widgets if w.field_type == "text"),
        len(checkboxes),
        len(groups),
        sum(1 for g in groups if g.exclusive),
        sum(1 for g in groups if g.review_required),
        len(claimed),
        len(checkboxes) - len(claimed),
    )
