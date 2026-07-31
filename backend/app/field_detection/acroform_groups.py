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
from dataclasses import dataclass, field

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
    frozenset({"ledig", "verheiratet", "verwitwet", "geschieden", "getrennt lebend"}),
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
        if _is_wrapped_continuation(previous, run) and not _text_between(
            previous, run, tokens
        ):
            merged[-1] = previous + run
        else:
            merged.append(run)
    return merged


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


def _label_right_of(
    rect: BoundingBox, tokens: tuple[DetectionToken, ...]
) -> str | None:
    """The nearest text immediately to a widget's right, on its own line.

    Used when a group's widgets all carry the *same* tooltip, which means the
    author put the question there rather than the option — the Stuttgart legal
    questions do exactly this, giving both boxes the tooltip "polizeiliches
    Ermittlungsverfahren". The distinguishing text ("ja", "nein") is then only
    available from the page itself.
    """
    centre_y = rect.y + rect.height / 2
    right = [
        token
        for token in tokens
        if token.bounding_box.x >= rect.x + rect.width - 1
        and token.bounding_box.x < rect.x + rect.width + 60
        and abs(token.bounding_box.y + token.bounding_box.height / 2 - centre_y)
        <= rect.height
    ]
    if not right:
        return None
    nearest = min(right, key=lambda t: t.bounding_box.x)
    return nearest.text.strip() or None


def _resolve_option_labels(
    options: tuple[WidgetOption, ...], tokens: tuple[DetectionToken, ...]
) -> tuple[tuple[WidgetOption, ...], str | None]:
    """Returns (options, shared_tooltip_used_as_question).

    When every widget in a group carries the same tooltip, that text is the
    question and cannot also be the answers. Each option's own label is then
    read from the page immediately to its right; if that fails the group is
    left alone, because two identically-labelled options are worse than one
    unlabelled group.
    """
    labels = {option.label for option in options}
    if len(labels) != 1:
        return options, None

    shared = next(iter(labels))
    rewritten: list[WidgetOption] = []
    for option in options:
        text = _label_right_of(option.rect, tokens)
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
    return tuple(rewritten), shared


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
                runs = _merge_wrapped_rows(runs, page_tokens)
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
                options, shared_question = _resolve_option_labels(options, page_tokens)

                box = _union([w.rect for w in run])
                labels = tuple(option.label for option in options)
                exclusive = _looks_exclusive(labels)
                groups.append(
                    WidgetGroup(
                        options=options,
                        page_number=page_number,
                        orientation=orientation,
                        # The author's own tooltip beats any geometric guess.
                        label=shared_question or _nearest_label_above(box, page_tokens),
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
