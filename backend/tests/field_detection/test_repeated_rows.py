"""Repeated table rows keep their own identity.

The Stuttgart application's children table produced twenty-eight independent
fields with nothing tying a row together, and the gender checkbox pairs — which
*did* group, one per row — all took their question from the table header.

The evidence is structural: several consecutive bands whose widgets sit at the
same x positions are the same question asked again. No vocabulary, no
field-name patterns, so an unanticipated table in an unanticipated language
behaves identically.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.field_detection.extraction import extract_native_document_input
from app.field_detection.providers.base import (
    AcroFormWidgetInput,
    BoundingBox,
    DetectionToken,
)
from app.field_detection.repeated_rows import (
    detect_repeated_sections,
    row_index_for_widget,
    section_widget_names,
)

_STUTTGART = Path("/Users/oussama/Downloads/32-41-1268-antrag-aufenthaltserlaubnis.pdf")


def _widget(
    name: str, x: float, y: float, kind: str = "text", width: float = 90.0
) -> AcroFormWidgetInput:
    return AcroFormWidgetInput(
        field_name=name,
        field_type=kind,
        rect=BoundingBox(x=x, y=y, width=width, height=14.0),
        page_number=1,
    )


def _token(text: str, x: float, y: float) -> DetectionToken:
    return DetectionToken(
        text=text,
        confidence=1.0,
        bounding_box=BoundingBox(x=x, y=y, width=len(text) * 5.0, height=9.0),
        source="native",
    )


def _table(rows: int, start_y: float = 100.0, step: float = 26.0):
    """A table of `rows` identical rows, three columns each."""
    widgets = []
    for row in range(rows):
        y = start_y + row * step
        widgets.append(_widget(f"name{row}", 60.0, y))
        widgets.append(_widget(f"born{row}", 200.0, y))
        widgets.append(_widget(f"city{row}", 340.0, y))
    return widgets


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def test_repeating_column_positions_identify_a_section() -> None:
    sections = detect_repeated_sections(_table(4), section_key="children")

    assert len(sections) == 1
    assert len(sections[0].rows) == 4


def test_two_identical_rows_are_not_a_section() -> None:
    """Two identical rows happen by coincidence in ordinary layouts; three do
    not."""
    assert detect_repeated_sections(_table(2)) == []


def test_rows_keep_their_order() -> None:
    section = detect_repeated_sections(_table(3), section_key="children")[0]

    assert [row.index for row in section.rows] == [1, 2, 3]
    # Row 1 is the topmost on the page.
    assert section.rows[0].bounding_box.y < section.rows[2].bounding_box.y


def test_rows_are_never_merged() -> None:
    """A child's details must never end up attached to their sibling."""
    section = detect_repeated_sections(_table(3), section_key="children")[0]

    for row in section.rows:
        assert len(row.cells) == 3
    names = [cell.widget_name for row in section.rows for cell in row.cells]
    assert len(names) == len(set(names))


def test_a_widget_belongs_to_exactly_one_row() -> None:
    section = detect_repeated_sections(_table(3), section_key="children")[0]

    assert row_index_for_widget([section], "name0") == ("children", 1)
    assert row_index_for_widget([section], "name2") == ("children", 3)
    assert row_index_for_widget([section], "not-in-the-table") is None


def test_rows_with_different_column_positions_are_not_one_section() -> None:
    """A layout that merely looks tabular must not be flattened into rows."""
    widgets = [
        _widget("a1", 60.0, 100.0),
        _widget("a2", 200.0, 100.0),
        _widget("a3", 340.0, 100.0),
        # Different columns: a different structure.
        _widget("b1", 90.0, 126.0),
        _widget("b2", 250.0, 126.0),
        _widget("b3", 400.0, 126.0),
        _widget("c1", 90.0, 152.0),
        _widget("c2", 250.0, 152.0),
        _widget("c3", 400.0, 152.0),
    ]

    sections = detect_repeated_sections(widgets)

    # The three matching rows form one section; the odd row out is excluded.
    assert all(len(section.rows) == 3 for section in sections)


def test_a_row_with_too_few_columns_is_not_a_section() -> None:
    widgets = [
        _widget("a1", 60.0, 100.0),
        _widget("a2", 200.0, 100.0),
        _widget("b1", 60.0, 126.0),
        _widget("b2", 200.0, 126.0),
        _widget("c1", 60.0, 152.0),
        _widget("c2", 200.0, 152.0),
    ]

    assert detect_repeated_sections(widgets) == []


# ---------------------------------------------------------------------------
# Keys
# ---------------------------------------------------------------------------


def test_indexed_keys_are_deterministic_and_unique() -> None:
    section = detect_repeated_sections(_table(3), section_key="children")[0]

    keys = [
        section.field_key(row.index, cell.column_key)
        for row in section.rows
        for cell in row.cells
    ]

    assert len(keys) == len(set(keys))
    assert keys[0].startswith("children_1_")
    assert any(key.startswith("children_3_") for key in keys)
    # Stable across runs: re-analysing must never rename a field.
    again = detect_repeated_sections(_table(3), section_key="children")[0]
    assert [c.column_key for r in again.rows for c in r.cells] == [
        c.column_key for r in section.rows for c in r.cells
    ]


def test_column_names_come_from_the_header_above_them() -> None:
    widgets = _table(3, start_y=100.0)
    header = (
        _token("Familienname", 60.0, 85.0),
        _token("Geburtsdatum", 200.0, 85.0),
        _token("Wohnort", 340.0, 85.0),
    )

    section = detect_repeated_sections(widgets, {1: header}, section_key="children")[0]

    assert section.column_keys == ("familienname", "geburtsdatum", "wohnort")


def test_a_sentence_above_a_column_is_not_used_as_its_name() -> None:
    """Positional is more honest than wrong: a long run above a column is prose
    that happened to land there, not a name for it."""
    widgets = _table(3, start_y=100.0)
    header = (
        _token(
            "Angaben sind auch erforderlich wenn diese Personen im Ausland verbleiben",
            60.0,
            85.0,
        ),
    )

    section = detect_repeated_sections(widgets, {1: header}, section_key="children")[0]

    assert section.column_keys[0] == "column_1"


def test_duplicate_header_words_never_collide_two_columns() -> None:
    widgets = _table(3, start_y=100.0)
    header = (
        _token("Datum", 60.0, 85.0),
        _token("Datum", 200.0, 85.0),
        _token("Ort", 340.0, 85.0),
    )

    section = detect_repeated_sections(widgets, {1: header}, section_key="children")[0]

    assert len(set(section.column_keys)) == 3


# ---------------------------------------------------------------------------
# The real document
# ---------------------------------------------------------------------------


def test_the_stuttgart_children_table_is_detected() -> None:
    if not _STUTTGART.exists():
        pytest.skip("Stuttgart PDF not available (real government document)")

    document = extract_native_document_input(_STUTTGART)
    sections = detect_repeated_sections(
        list(document.acroform_widgets),
        {page.page_number: page.tokens for page in document.pages},
        section_key="children",
    )

    children = next(s for s in sections if s.key == "children")
    assert len(children.rows) >= 4
    # The columns the form actually offers, named from its own header.
    assert "familienname" in children.column_keys
    assert "wohnort" in children.column_keys

    # Every cell belongs to exactly one row, and no key repeats.
    keys = [
        children.field_key(row.index, cell.column_key)
        for row in children.rows
        for cell in row.cells
    ]
    assert len(keys) == len(set(keys))

    # A row's own widgets resolve to that row and no other.
    first_row_widget = children.rows[0].cells[0].widget_name
    assert row_index_for_widget(sections, first_row_widget) == ("children", 1)
    assert len(section_widget_names(sections)) == len(
        {c.widget_name for s in sections for r in s.rows for c in r.cells}
    )
