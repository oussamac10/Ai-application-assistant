"""Repeated table rows: one section, many rows, stable identities.

The Stuttgart application has a children table — four rows, each with family
name, first name, gender, birth date and place, nationality and residence. The
AcroForm pass emitted twenty-eight independent fields with no idea that any of
them belonged together, and the gender checkbox pairs (which *did* group, one
per row) took their question from the table header, so all four read
"Familienname Vorname(n) männ- lich weib- lich".

The evidence that these are repeated rows is entirely structural, and stronger
than it first looks:

    y=580.7  x= 65.9  168.2  [251.1 276.6]  296.4  388.9  448.6
    y=606.5  x= 65.9  168.2  [251.1 276.6]  296.4  388.9  448.6
    y=632.5  x= 65.9  168.2  [251.1 276.6]  296.4  388.9  448.6

Several consecutive bands whose widgets sit at the *same x positions* are the
same question asked again. That is a column signature, and it identifies a
repeated section without reading a single word — no vocabulary, no field-name
patterns, no table-specific rules. A form nobody anticipated, in a language
nobody anticipated, produces the same answer.

Two things this deliberately does not do. It does not merge rows: each row keeps
its own identity and its own widget references, because a child's gender must
never end up attached to their sibling. And it does not invent a row that the
document did not draw: a band with no widgets is not a row.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.field_detection.providers.base import (
    AcroFormWidgetInput,
    BoundingBox,
    DetectionToken,
)

logger = logging.getLogger(__name__)

# Two widgets are in the same column when their left edges differ by less than
# this many points. Generous enough for the sub-point drift real generators
# produce, tight enough that neighbouring columns never merge — the narrowest
# gap on the reference table is 25pt.
_COLUMN_TOLERANCE = 4.0

# Two widgets are in the same row band when their vertical centres differ by
# less than this multiple of the taller one's height.
_ROW_TOLERANCE = 0.6

# Below this many repeats it is not a repeated section — two identical rows can
# happen by coincidence in an ordinary layout, three cannot.
_MIN_REPEATS = 3

# A row must offer at least this many columns before it is worth treating as a
# section rather than as independent fields.
_MIN_COLUMNS = 3

# A column name longer than this is a sentence that happened to sit above the
# column, not a name for it.
_MAX_COLUMN_KEY_LENGTH = 40

# Widget types that select rather than accept typing. A run of these inside one
# row is one question.
_SELECTION_TYPES = frozenset({"checkbox", "radio"})


@dataclass(frozen=True)
class RowChoiceOption:
    """One selectable widget inside a row's choice cell.

    `source_label` is the document's own wording, kept verbatim; export writes
    back to `widget_name` at `rect`.
    """

    source_label: str
    widget_name: str
    rect: BoundingBox
    export_value: str | None = None


@dataclass(frozen=True)
class RowCell:
    """One field inside a repeated row, with everything export needs.

    A cell is usually one widget. It is several when adjacent columns in the
    row are selection controls that together ask one question — the children
    table's männlich/weiblich pair is two checkbox columns and one question
    about one child.
    """

    column_index: int
    column_key: str
    widget_name: str
    field_type: str
    rect: BoundingBox
    options: tuple[RowChoiceOption, ...] = ()

    @property
    def widget_names(self) -> tuple[str, ...]:
        """Every widget this cell writes to. Export needs all of them."""
        if self.options:
            return tuple(option.widget_name for option in self.options)
        return (self.widget_name,)


@dataclass(frozen=True)
class RepeatedRow:
    """One row of a repeated section. `index` is 1-based and follows reading
    order, so `children_2_*` is always the second row on the page."""

    index: int
    cells: tuple[RowCell, ...]
    bounding_box: BoundingBox


@dataclass(frozen=True)
class RepeatedSection:
    """A run of rows that ask the same questions."""

    key: str
    page_number: int
    rows: tuple[RepeatedRow, ...]
    column_keys: tuple[str, ...]
    ignored_empty_rows: int = 0

    def field_key(self, row_index: int, column_key: str) -> str:
        """The deterministic indexed key for one cell.

        Stable across runs and unique by construction, so re-analysing a
        document never renames a field and two rows can never collide.
        """
        return f"{self.key}_{row_index}_{column_key}"


def _centre_y(rect: BoundingBox) -> float:
    return rect.y + rect.height / 2


def _row_bands(
    widgets: list[AcroFormWidgetInput],
) -> list[list[AcroFormWidgetInput]]:
    """Groups widgets into horizontal bands.

    A checkbox sits slightly lower than the text field beside it (589.4 against
    580.7 on the reference form), so bands are built from vertical *overlap*
    rather than equal tops — otherwise every row would split in two.
    """
    bands: list[list[AcroFormWidgetInput]] = []
    for widget in sorted(widgets, key=lambda w: (_centre_y(w.rect), w.rect.x)):
        centre = _centre_y(widget.rect)
        placed = False
        for band in bands:
            reference = max(band, key=lambda w: w.rect.height)
            tolerance = max(reference.rect.height, widget.rect.height) * _ROW_TOLERANCE
            if abs(centre - _centre_y(reference.rect)) <= tolerance:
                band.append(widget)
                placed = True
                break
        if not placed:
            bands.append([widget])
    return [sorted(band, key=lambda w: w.rect.x) for band in bands]


def _column_signature(band: list[AcroFormWidgetInput]) -> tuple[int, ...]:
    """A band's column positions, quantised.

    Rounding to the tolerance is what lets two rows compare equal despite the
    sub-point drift real PDF generators produce.
    """
    return tuple(int(round(widget.rect.x / _COLUMN_TOLERANCE)) for widget in band)


def _column_key(
    index: int, rect: BoundingBox, header_tokens: tuple[DetectionToken, ...]
) -> str:
    """A stable name for a column, from its header if one is readable.

    Falls back to a positional name rather than an invented one: `column_3` is
    honest about knowing nothing, while a guessed word would look like a
    finding.
    """
    from app.field_detection.normalization import normalize_field_name

    # A token belongs to this column only if its *centre* falls inside it.
    # Overlap alone lets a wide header word bleed into both neighbours, which
    # produced keys like "erforderlich_vorname_n_wenn_diese_personen".
    inside = [
        token
        for token in header_tokens
        if rect.x
        <= token.bounding_box.x + token.bounding_box.width / 2
        <= rect.x + rect.width
    ]
    if inside:
        # Only the header line closest to the row. A multi-line header
        # otherwise concatenates every line into one unreadable key.
        lowest = max(token.bounding_box.y for token in inside)
        line = [
            token
            for token in inside
            if abs(token.bounding_box.y - lowest) <= token.bounding_box.height
        ]
        text = " ".join(
            token.text for token in sorted(line, key=lambda t: t.bounding_box.x)
        ).strip()
        key = normalize_field_name(text)
        # A long key is a sentence that happened to sit above the column, not a
        # column name. Positional is more honest than wrong.
        if key and key != "field" and len(key) <= _MAX_COLUMN_KEY_LENGTH:
            return key
    return f"column_{index + 1}"


def _union(rects: list[BoundingBox]) -> BoundingBox:
    x0 = min(r.x for r in rects)
    y0 = min(r.y for r in rects)
    x1 = max(r.x + r.width for r in rects)
    y1 = max(r.y + r.height for r in rects)
    return BoundingBox(x=x0, y=y0, width=x1 - x0, height=y1 - y0)


def detect_repeated_sections(
    widgets: list[AcroFormWidgetInput],
    tokens_by_page: dict[int, tuple[DetectionToken, ...]] | None = None,
    section_key: str = "row",
) -> list[RepeatedSection]:
    """Finds runs of consecutive bands that share a column signature.

    `section_key` names the section; callers that can identify the table (from
    a caption, say) pass something better than the default.
    """
    tokens_by_page = tokens_by_page or {}
    sections: list[RepeatedSection] = []

    by_page: dict[int, list[AcroFormWidgetInput]] = {}
    for widget in widgets:
        by_page.setdefault(widget.page_number, []).append(widget)

    for page_number, page_widgets in sorted(by_page.items()):
        bands = _row_bands(page_widgets)
        page_tokens = tokens_by_page.get(page_number, ())

        index = 0
        while index < len(bands):
            signature = _column_signature(bands[index])
            if len(signature) < _MIN_COLUMNS:
                index += 1
                continue

            run = [bands[index]]
            probe = index + 1
            while probe < len(bands) and _column_signature(bands[probe]) == signature:
                run.append(bands[probe])
                probe += 1

            if len(run) < _MIN_REPEATS:
                index += 1
                continue

            sections.append(
                _build_section(
                    page_number, run, page_tokens, section_key, len(sections)
                )
            )
            index = probe

    _log_counts(sections)
    return sections


def _build_section(
    page_number: int,
    run: list[list[AcroFormWidgetInput]],
    page_tokens: tuple[DetectionToken, ...],
    section_key: str,
    ordinal: int,
) -> RepeatedSection:
    # Column names come from the text directly above the first row, which is
    # the table header. Read once for the section so every row names its
    # columns identically.
    first_top = min(w.rect.y for w in run[0])
    header_tokens = tuple(
        token
        for token in page_tokens
        if first_top - 60 < token.bounding_box.y < first_top
    )
    column_keys = tuple(
        _column_key(position, widget.rect, header_tokens)
        for position, widget in enumerate(run[0])
    )
    # A duplicate header word would collide two columns into one key; position
    # disambiguates rather than silently overwriting.
    column_keys = _make_unique(column_keys)

    rows = tuple(
        RepeatedRow(
            index=row_index + 1,
            cells=_merge_choice_cells(
                tuple(
                    RowCell(
                        column_index=position,
                        column_key=column_keys[position],
                        widget_name=widget.field_name,
                        field_type=widget.field_type,
                        rect=widget.rect,
                    )
                    for position, widget in enumerate(band)
                    if position < len(column_keys)
                ),
                band,
            ),
            bounding_box=_union([w.rect for w in band]),
        )
        for row_index, band in enumerate(run)
    )

    key = section_key if ordinal == 0 else f"{section_key}_{ordinal + 1}"
    return RepeatedSection(
        key=key,
        page_number=page_number,
        rows=rows,
        column_keys=column_keys,
    )


def _merge_choice_cells(
    cells: tuple[RowCell, ...], band: list[AcroFormWidgetInput]
) -> tuple[RowCell, ...]:
    """Collapses adjacent selection-control columns into one choice cell.

    The children table gives each child two checkbox columns, männlich and
    weiblich. Left as two cells they are two questions about one person, and
    the answer to "is this child male?" is not a field a form is asking for.

    The rule is positional: a run of consecutive checkbox/radio columns inside
    one row is one question. Naming it is the only place a recognised option
    set is consulted, and only to *improve* the name — an unrecognised pair
    still merges, and falls back to a positional key.
    """
    from app.field_detection.option_groups import match_option_set

    merged: list[RowCell] = []
    index = 0
    while index < len(cells):
        cell = cells[index]
        if cell.field_type not in _SELECTION_TYPES:
            merged.append(cell)
            index += 1
            continue

        run_end = index
        while (
            run_end + 1 < len(cells)
            and cells[run_end + 1].field_type in _SELECTION_TYPES
        ):
            run_end += 1

        if run_end == index:
            # A lone checkbox in a row is a boolean, not a choice.
            merged.append(cell)
            index += 1
            continue

        run = cells[index : run_end + 1]
        options = tuple(
            RowChoiceOption(
                source_label=_widget_label(member, band),
                widget_name=member.widget_name,
                rect=member.rect,
                export_value=_widget_export_value(member, band),
            )
            for member in run
        )
        labels = tuple(option.source_label for option in options)
        recognised = match_option_set(labels)
        merged.append(
            RowCell(
                column_index=cell.column_index,
                column_key=recognised.key if recognised else "choice",
                # The first widget names the cell; `widget_names` exposes all
                # of them, and export needs every rectangle.
                widget_name=cell.widget_name,
                field_type="single_choice",
                rect=_union([member.rect for member in run]),
                options=options,
            )
        )
        index = run_end + 1

    return tuple(merged)


def _widget_label(cell: RowCell, band: list[AcroFormWidgetInput]) -> str:
    """The document's own wording for one option, kept verbatim."""
    for widget in band:
        if widget.field_name == cell.widget_name:
            return (widget.field_label or "").strip() or cell.column_key
    return cell.column_key


def _widget_export_value(cell: RowCell, band: list[AcroFormWidgetInput]) -> str | None:
    for widget in band:
        if widget.field_name == cell.widget_name:
            return widget.export_value
    return None


def _make_unique(keys: tuple[str, ...]) -> tuple[str, ...]:
    seen: dict[str, int] = {}
    unique: list[str] = []
    for position, key in enumerate(keys):
        if key in seen:
            unique.append(f"{key}_{position + 1}")
        else:
            seen[key] = position
            unique.append(key)
    return tuple(unique)


def section_widget_names(sections: list[RepeatedSection]) -> set[str]:
    """Every widget a repeated section accounts for."""
    return {
        cell.widget_name
        for section in sections
        for row in section.rows
        for cell in row.cells
    }


def section_choice_widget_names(sections: list[RepeatedSection]) -> set[str]:
    """Widgets already answered by a choice cell inside a repeated row.

    The AcroForm pass skips any group made entirely of these, so a child's
    gender is asked once — as part of that child's row — rather than twice.
    """
    return {
        option.widget_name
        for section in sections
        for row in section.rows
        for cell in row.cells
        for option in cell.options
    }


def row_index_for_widget(
    sections: list[RepeatedSection], widget_name: str
) -> tuple[str, int] | None:
    """The section key and 1-based row a widget belongs to, if any.

    Used to give a row's own controls a row-specific question — "Gender —
    Child 2" rather than the table header repeated four times.
    """
    for section in sections:
        for row in section.rows:
            if any(cell.widget_name == widget_name for cell in row.cells):
                return section.key, row.index
    return None


def _log_counts(sections: list[RepeatedSection]) -> None:
    """Counts only. A children table holds names and birthplaces; none of it
    reaches a log."""
    if not sections:
        return
    logger.info(
        "Repeated sections: repeated_sections_detected=%d repeated_rows_detected=%d "
        "repeated_rows_ignored_empty=%d repeated_fields_generated=%d "
        "repeated_widget_associations=%d",
        len(sections),
        sum(len(section.rows) for section in sections),
        sum(section.ignored_empty_rows for section in sections),
        sum(len(row.cells) for section in sections for row in section.rows),
        len(section_widget_names(sections)),
    )
