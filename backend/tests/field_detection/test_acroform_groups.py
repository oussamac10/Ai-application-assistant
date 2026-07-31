"""Grouping native AcroForm checkbox widgets into single questions.

The AcroForm path emitted one candidate per widget, so a fillable government
form asked fifty-four questions where a reader sees about a dozen — and because
that path bypasses the text-line passes entirely, none of the visual grouping
built earlier in this phase applied to it.

`/Kids` and the radio flag do not help: every checkbox on the reference document
is an independent field with `flags=0`. The grouping evidence is geometry, which
is what a reader uses too — collinear, evenly spaced widgets belong together,
and a gap that jumps ends the group.
"""

from __future__ import annotations

import pytest

from app.field_detection.acroform_groups import (
    claimed_widget_names,
    group_checkbox_widgets,
    is_machine_name,
)
from app.field_detection.providers.base import (
    AcroFormWidgetInput,
    BoundingBox,
    DetectionToken,
)


def _checkbox(
    name: str, label: str, x: float, y: float, page: int = 1
) -> AcroFormWidgetInput:
    return AcroFormWidgetInput(
        field_name=name,
        field_type="checkbox",
        rect=BoundingBox(x=x, y=y, width=12.8, height=12.8),
        page_number=page,
        field_label=label,
        export_value="Ja",
    )


def _token(text: str, x: float, y: float) -> DetectionToken:
    return DetectionToken(
        text=text,
        confidence=1.0,
        bounding_box=BoundingBox(x=x, y=y, width=len(text) * 5.0, height=10.0),
        source="native",
    )


# ---------------------------------------------------------------------------
# Geometry decides the grouping
# ---------------------------------------------------------------------------


def test_a_row_of_options_becomes_one_group() -> None:
    """Family status on the reference form: same y, varying x."""
    widgets = [
        _checkbox("chkLedig", "ledig", 67.9, 374.8),
        _checkbox("chkVerh", "verheiratet", 114.3, 374.8),
        _checkbox("chkWitwe", "verwitwet", 237.8, 374.8),
        _checkbox("chkGesch", "geschieden", 295.9, 374.8),
        _checkbox("chkTrenn", "getrennt lebend", 364.1, 374.8),
    ]

    groups = group_checkbox_widgets(widgets)

    assert len(groups) == 1
    assert [option.label for option in groups[0].options] == [
        "ledig",
        "verheiratet",
        "verwitwet",
        "geschieden",
        "getrennt lebend",
    ]
    assert groups[0].orientation == "row"


def test_a_column_of_options_becomes_one_group() -> None:
    """Application purpose: same x, regular y steps."""
    widgets = [
        _checkbox("chkAzubi", "Ausbildung", 67.9, 95.8),
        _checkbox("chkErwerb", "Erwerbstätigkeit", 67.9, 110.7),
        _checkbox("chkPol", "völkerrechtliche Gründe", 67.9, 124.6),
        _checkbox("chkFam", "Familiennachzug", 67.9, 138.5),
    ]

    groups = group_checkbox_widgets(widgets)

    assert len(groups) == 1
    assert groups[0].orientation == "column"
    assert len(groups[0].options) == 4


def test_a_gap_that_jumps_ends_the_group() -> None:
    """Two unrelated questions on the same row must not merge."""
    widgets = [
        _checkbox("a1", "ja", 100.0, 200.0),
        _checkbox("a2", "nein", 130.0, 200.0),
        # Far away: a different question.
        _checkbox("b1", "Sprachkurs", 420.0, 200.0),
        _checkbox("b2", "Studium", 450.0, 200.0),
    ]

    groups = group_checkbox_widgets(widgets)

    assert len(groups) == 2
    assert {option.label for option in groups[0].options} == {"ja", "nein"}
    assert {option.label for option in groups[1].options} == {"Sprachkurs", "Studium"}


def test_a_lone_checkbox_is_not_a_group() -> None:
    """One checkbox is a boolean, and must stay an independent question."""
    groups = group_checkbox_widgets(
        [_checkbox("consent", "Ich stimme zu", 60.0, 300.0)]
    )

    assert groups == []


def test_grouping_never_consults_vocabulary() -> None:
    """An unanticipated option set on an unanticipated form groups for the same
    geometric reason as a recognised one."""
    widgets = [
        _checkbox("w1", "Zzyzx", 60.0, 100.0),
        _checkbox("w2", "Qwerty", 120.0, 100.0),
        _checkbox("w3", "Fnord", 180.0, 100.0),
    ]

    groups = group_checkbox_widgets(widgets)

    assert len(groups) == 1
    assert len(groups[0].options) == 3
    # Unrecognised, so the single/multiple decision is flagged rather than
    # guessed — but the group is preserved either way.
    assert groups[0].review_required is True


def test_a_recognised_exclusive_set_is_not_flagged_for_review() -> None:
    widgets = [
        _checkbox("y", "ja", 100.0, 200.0),
        _checkbox("n", "nein", 130.0, 200.0),
    ]

    groups = group_checkbox_widgets(widgets)

    assert groups[0].exclusive is True
    assert groups[0].review_required is False


def test_widgets_on_different_pages_never_group() -> None:
    widgets = [
        _checkbox("p1", "ja", 100.0, 200.0, page=1),
        _checkbox("p2", "nein", 130.0, 200.0, page=2),
    ]

    assert group_checkbox_widgets(widgets) == []


# ---------------------------------------------------------------------------
# Labels
# ---------------------------------------------------------------------------


def test_option_labels_come_from_the_tooltip() -> None:
    """The author's own tooltip is human text; the field name is not."""
    widgets = [
        _checkbox("chkLedigS1", "ledig", 67.9, 374.8),
        _checkbox("chkVerhS1", "verheiratet", 114.3, 374.8),
    ]

    options = group_checkbox_widgets(widgets)[0].options

    assert [option.label for option in options] == ["ledig", "verheiratet"]
    # The machine name survives for export, which has to write back to it.
    assert [option.widget_name for option in options] == ["chkLedigS1", "chkVerhS1"]
    assert all(option.export_value == "Ja" for option in options)


def test_a_tooltip_shared_by_every_widget_is_the_question() -> None:
    """The reference form gives both boxes of a legal question the tooltip
    "polizeiliches Ermittlungsverfahren" — that is the question, and it cannot
    also be both answers. The distinguishing text is only on the page."""
    widgets = [
        _checkbox("c1", "polizeiliches Ermittlungsverfahren", 400.0, 300.0),
        _checkbox("c2", "polizeiliches Ermittlungsverfahren", 440.0, 300.0),
    ]
    tokens = (_token("ja", 415.0, 300.0), _token("nein", 455.0, 300.0))

    group = group_checkbox_widgets(widgets, {1: tokens})[0]

    assert group.label == "polizeiliches Ermittlungsverfahren"
    assert [option.label for option in group.options] == ["ja", "nein"]


def test_a_shared_tooltip_with_no_page_text_leaves_the_group_alone() -> None:
    """Two identically-labelled options are worse than one unlabelled group."""
    widgets = [
        _checkbox("c1", "Krankenversicherung", 400.0, 300.0),
        _checkbox("c2", "Krankenversicherung", 440.0, 300.0),
    ]

    group = group_checkbox_widgets(widgets, {1: ()})[0]

    assert group.label != "Krankenversicherung" or group.label is None


def test_the_group_question_is_read_from_the_text_above() -> None:
    widgets = [
        _checkbox("a", "Einzelzimmer", 60.0, 300.0),
        _checkbox("b", "Sammelunterkunft", 160.0, 300.0),
    ]
    tokens = (
        _token("Wie", 60.0, 280.0),
        _token("sind", 80.0, 280.0),
        _token("Sie", 105.0, 280.0),
        _token("untergebracht?", 125.0, 280.0),
    )

    group = group_checkbox_widgets(widgets, {1: tokens})[0]

    assert group.label == "Wie sind Sie untergebracht?"


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Checkbox17", True),
        ("chkAzubi", True),
        ("Field_1", True),
        ("Group42", True),
        ("Familienstand", False),
        ("", True),
        (None, True),
    ],
)
def test_machine_name_recognition(name: str | None, expected: bool) -> None:
    assert is_machine_name(name) is expected


# ---------------------------------------------------------------------------
# Claiming
# ---------------------------------------------------------------------------


def test_grouped_widgets_are_reported_as_claimed() -> None:
    """The AcroForm pass skips these, so a grouped checkbox is never also
    emitted as its own question."""
    widgets = [
        _checkbox("a", "ja", 100.0, 200.0),
        _checkbox("b", "nein", 130.0, 200.0),
        _checkbox("lonely", "Ich stimme zu", 60.0, 500.0),
    ]

    groups = group_checkbox_widgets(widgets)

    assert claimed_widget_names(groups) == {"a", "b"}


def test_text_widgets_are_never_grouped() -> None:
    text_widget = AcroFormWidgetInput(
        field_name="surname",
        field_type="text",
        rect=BoundingBox(x=100.0, y=200.0, width=200.0, height=14.0),
        page_number=1,
    )

    assert group_checkbox_widgets([text_widget]) == []
