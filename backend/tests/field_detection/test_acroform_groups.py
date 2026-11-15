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
    claimed_widgets,
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

    assert {identity[0] for identity in claimed_widgets(groups)} == {"a", "b"}


def test_two_widgets_sharing_one_field_name_are_both_claimed() -> None:
    """Identity is position, not name. The reference form gives both boxes of a
    ja/nein question the same field name, distinguishing them only by export
    value — counting names reported 54 grouped widgets as "49 claimed"."""
    widgets = [
        _checkbox("chkVorstrafeS3", "Vorstrafe", 400.0, 300.0),
        _checkbox("chkVorstrafeS3", "Vorstrafe", 440.0, 300.0),
    ]

    groups = group_checkbox_widgets(
        widgets, {1: (_token("ja", 415.0, 300.0), _token("nein", 455.0, 300.0))}
    )

    assert len(claimed_widgets(groups)) == 2


def test_a_wrapped_option_list_becomes_one_group() -> None:
    """Six options laid out three-and-three are one question."""
    widgets = [
        _checkbox("a", "Sprachkurs", 60.0, 660.0),
        _checkbox("b", "Studium", 160.0, 660.0),
        _checkbox("c", "Arbeitsaufnahme", 260.0, 660.0),
        _checkbox("d", "Werkvertrag", 60.0, 675.0),
        _checkbox("e", "Au-Pair", 160.0, 675.0),
        _checkbox("f", "Sonstiges", 260.0, 675.0),
    ]

    groups = group_checkbox_widgets(widgets)

    assert len(groups) == 1
    assert len(groups[0].options) == 6


def test_question_text_between_two_rows_prevents_a_merge() -> None:
    """Geometry alone says "continuation" for two adjacent, identically
    aligned rows. The second question's printed text is what separates them."""
    widgets = [
        _checkbox("a", "Einzelzimmer", 60.0, 660.0),
        _checkbox("b", "Sammelunterkunft", 160.0, 660.0),
        _checkbox("c", "Sprachkurs", 60.0, 682.0),
        _checkbox("d", "Studium", 160.0, 682.0),
    ]
    # A new question printed to the left of the options, between the rows.
    tokens = (_token("20 Zweck des Aufenthalts", 20.0, 675.0),)

    groups = group_checkbox_widgets(widgets, {1: tokens})

    assert len(groups) == 2


def test_rows_with_different_shared_tooltips_never_merge() -> None:
    """Native evidence outranks geometry: two consecutive legal questions align
    too well for any positional test, but the author labelled them apart."""
    widgets = [
        _checkbox("q1", "Ermittlungsverfahren", 400.0, 300.0),
        _checkbox("q1", "Ermittlungsverfahren", 440.0, 300.0),
        _checkbox("q2", "Strafbefehl", 400.0, 315.0),
        _checkbox("q2", "Strafbefehl", 440.0, 315.0),
    ]
    tokens = tuple(
        _token(text, x, y)
        for text, x, y in (
            ("ja", 415.0, 300.0),
            ("nein", 455.0, 300.0),
            ("ja", 415.0, 315.0),
            ("nein", 455.0, 315.0),
        )
    )

    groups = group_checkbox_widgets(widgets, {1: tokens})

    assert len(groups) == 2
    assert {g.label for g in groups} == {"Ermittlungsverfahren", "Strafbefehl"}


def test_text_widgets_are_never_grouped() -> None:
    text_widget = AcroFormWidgetInput(
        field_name="surname",
        field_type="text",
        rect=BoundingBox(x=100.0, y=200.0, width=200.0, height=14.0),
        page_number=1,
    )

    assert group_checkbox_widgets([text_widget]) == []


# ---------------------------------------------------------------------------
# Option-label association (the "Bundesrepublik" regression)
# ---------------------------------------------------------------------------


def _legal_row_tokens() -> tuple[DetectionToken, ...]:
    """The reference form's "Ausweisung" row, to scale.

    The question wraps onto the line above the checkboxes and its last words
    sit almost exactly over the option labels: `Bundesrepublik` at x=140.7 is
    0.2pt to the *left* of `nein` at x=140.9. A nearest-by-x search picked the
    question word.
    """
    return tuple(
        DetectionToken(
            text=text,
            confidence=1.0,
            bounding_box=BoundingBox(x=x, y=y, width=len(text) * 4.2, height=9.0),
            source="native",
        )
        for text, x, y in (
            ("eine", 70.0, 409.0),
            ("Einreise", 87.6, 409.0),
            ("in", 118.9, 409.0),
            ("die", 127.6, 409.0),
            ("Bundesrepublik", 140.7, 409.0),
            ("Deutschland", 198.3, 409.0),
            ("ja", 84.2, 422.0),
            ("nein", 140.9, 422.0),
        )
    )


def test_the_question_line_above_is_never_used_as_an_option_label() -> None:
    """The reported bug, at the real coordinates."""
    widgets = [
        _checkbox("chkAusweisungS3", "Ausweisung", 67.9, 420.9),
        _checkbox("chkAusweisungS3", "Ausweisung", 124.7, 420.7),
    ]

    group = group_checkbox_widgets(widgets, {1: _legal_row_tokens()})[0]

    labels = [option.label for option in group.options]
    assert labels == ["ja", "nein"]
    assert "Bundesrepublik" not in labels


def test_same_baseline_text_beats_closer_text_on_another_line() -> None:
    """Vertical agreement is decided first and strictly: a label shares the
    widget's baseline, and anything on another line is a different sentence
    however close it looks horizontally."""
    widgets = [
        _checkbox("q", "shared", 100.0, 200.0),
        _checkbox("q", "shared", 200.0, 200.0),
    ]
    tokens = (
        # Horizontally nearer, but on the line above.
        DetectionToken(
            text="Wrong",
            confidence=1.0,
            bounding_box=BoundingBox(x=214.0, y=188.0, width=25.0, height=9.0),
            source="native",
        ),
        DetectionToken(
            text="ja",
            confidence=1.0,
            bounding_box=BoundingBox(x=116.0, y=201.0, width=8.0, height=9.0),
            source="native",
        ),
        DetectionToken(
            text="nein",
            confidence=1.0,
            bounding_box=BoundingBox(x=216.0, y=201.0, width=16.0, height=9.0),
            source="native",
        ),
    )

    group = group_checkbox_widgets(widgets, {1: tokens})[0]

    assert [option.label for option in group.options] == ["ja", "nein"]


def test_a_long_word_run_beside_a_widget_is_not_an_option() -> None:
    """A long phrase next to a checkbox is the question, prose, or the next
    column — never the answer. Left unresolved, the group keeps its shared
    tooltip rather than being given wrong labels."""
    widgets = [
        _checkbox("q", "Krankenversicherung", 100.0, 200.0),
        _checkbox("q", "Krankenversicherung", 200.0, 200.0),
    ]
    tokens = (
        DetectionToken(
            text="besteht fuer die gesamte Dauer des Aufenthalts",
            confidence=1.0,
            bounding_box=BoundingBox(x=116.0, y=201.0, width=200.0, height=9.0),
            source="native",
        ),
    )

    group = group_checkbox_widgets(widgets, {1: tokens})[0]

    # Unchanged rather than wrong: two identically-labelled options are worse
    # than one unlabelled group, and this stays reviewable.
    assert {option.label for option in group.options} == {"Krankenversicherung"}


def test_neighbouring_legal_rows_keep_their_own_options() -> None:
    widgets = [
        _checkbox("q1", "Ermittlungsverfahren", 100.0, 200.0),
        _checkbox("q1", "Ermittlungsverfahren", 200.0, 200.0),
        _checkbox("q2", "Strafbefehl", 100.0, 215.0),
        _checkbox("q2", "Strafbefehl", 200.0, 215.0),
    ]
    tokens = tuple(
        DetectionToken(
            text=text,
            confidence=1.0,
            bounding_box=BoundingBox(x=x, y=y, width=len(text) * 4.2, height=9.0),
            source="native",
        )
        for text, x, y in (
            ("ja", 116.0, 201.0),
            ("nein", 216.0, 201.0),
            ("ja", 116.0, 216.0),
            ("nein", 216.0, 216.0),
        )
    )

    groups = group_checkbox_widgets(widgets, {1: tokens})

    assert len(groups) == 2
    for group in groups:
        assert [option.label for option in group.options] == ["ja", "nein"]
    # And no widget was lost between them.
    assert len(claimed_widgets(groups)) == 4


# ---------------------------------------------------------------------------
# Row-scoped groups inside repeated tables
# ---------------------------------------------------------------------------


def _gender_rows() -> list[AcroFormWidgetInput]:
    """Six identical gender pairs, one per child row — the shape that merged."""
    return [
        _checkbox(f"chkMann{row}", "männlich", 251.1, 589.4 + row * 26.0)
        for row in range(6)
    ] + [
        _checkbox(f"chkFrau{row}", "weiblich", 276.6, 589.4 + row * 26.0)
        for row in range(6)
    ]


def test_per_row_groups_are_never_merged_into_one() -> None:
    """Each child's gender is a separate question about a separate person.

    Every other guard says "wrapped continuation": the pairs share a left edge,
    a widget size and a spacing, and the cells between them are *widgets*
    rather than text. Only the row model separates them.
    """
    rows = {f"chkMann{r}": ("row", r + 1) for r in range(6)}
    rows.update({f"chkFrau{r}": ("row", r + 1) for r in range(6)})

    groups = group_checkbox_widgets(
        _gender_rows(), None, row_lookup=lambda name: rows.get(name)
    )

    assert len(groups) == 6
    for group in groups:
        assert len(group.options) == 2


def test_a_per_row_group_is_named_after_its_own_row() -> None:
    """ "männlich / weiblich — row 2", not the table header repeated six times
    with nothing saying which child it is about."""
    rows = {f"chkMann{r}": ("row", r + 1) for r in range(6)}
    rows.update({f"chkFrau{r}": ("row", r + 1) for r in range(6)})

    groups = group_checkbox_widgets(
        _gender_rows(), None, row_lookup=lambda name: rows.get(name)
    )

    labels = [group.label for group in groups]
    assert labels[0] == "männlich / weiblich — row 1"
    assert labels[5] == "männlich / weiblich — row 6"
    # Every row is distinguishable from every other.
    assert len(set(labels)) == 6


def test_without_a_row_model_nothing_changes() -> None:
    """The lookup is injected, so a caller that has no table information gets
    exactly the previous behaviour."""
    groups = group_checkbox_widgets(
        [
            _checkbox("a", "ja", 100.0, 200.0),
            _checkbox("b", "nein", 130.0, 200.0),
        ]
    )

    assert len(groups) == 1
    assert groups[0].label != "ja / nein — row 1"


def test_generic_shared_tooltip_uses_heading_and_resolves_multiword_and_wrapped_options() -> (
    None
):
    """When every checkbox on a page carries a generic tooltip like 'ja',
    each group must still get its own heading above and full option labels
    (including multi-word 'getrennt lebend' and wrapped 'Aufenthalts- / erlaubnis'),
    so neither group collides as 'ja' during deduplication."""
    from app.field_detection.providers.base import (
        DetectionDocumentInput,
        DetectionPageInput,
    )
    from app.field_detection.providers.local import LocalFieldDetectionProvider

    widgets = [
        _checkbox("chkAufenthalt", "ja", 188.0, 410.0),
        _checkbox("chkNieder", "ja", 282.0, 410.0),
        _checkbox("chkDuldung", "ja", 377.0, 410.0),
        _checkbox("chkSonstige", "ja", 471.0, 410.0),
        _checkbox("chkLedig", "ja", 67.0, 486.0),
        _checkbox("chkVerheiratet", "ja", 119.0, 486.0),
        _checkbox("chkLebenspartner", "ja", 198.0, 486.0),
        _checkbox("chkVerwitwet", "ja", 316.0, 486.0),
        _checkbox("chkGeschieden", "ja", 389.0, 486.0),
        _checkbox("chkGetrennt", "ja", 466.0, 486.0),
    ]
    tokens = (
        _token("Aufenthaltsstatus", 70.0, 397.0),
        _token("Aufenthalts-", 203.0, 412.0),
        _token("erlaubnis", 203.0, 422.0),
        _token("Niederlassungs-", 298.0, 412.0),
        _token("erlaubnis", 298.0, 422.0),
        _token("Duldung", 392.0, 412.0),
        _token("sonstiger", 487.0, 412.0),
        _token("Status", 487.0, 422.0),
        _token("Familienstand", 70.0, 469.0),
        _token("ledig", 83.0, 488.0),
        _token("verheiratet", 136.0, 488.0),
        _token("Lebenspartnerschaft", 213.0, 488.0),
        _token("verwitwet", 333.0, 488.0),
        _token("geschieden", 405.0, 488.0),
        _token("getrennt", 482.0, 488.0),
        _token("lebend", 525.0, 488.0),
    )

    groups = group_checkbox_widgets(widgets, {1: tokens})
    assert len(groups) == 2
    assert groups[0].label == "Aufenthaltsstatus"
    assert [o.label for o in groups[0].options] == [
        "Aufenthaltserlaubnis",
        "Niederlassungserlaubnis",
        "Duldung",
        "sonstiger Status",
    ]
    assert groups[1].label == "Familienstand"
    assert groups[1].exclusive is True
    assert [o.label for o in groups[1].options] == [
        "ledig",
        "verheiratet",
        "Lebenspartnerschaft",
        "verwitwet",
        "geschieden",
        "getrennt lebend",
    ]

    doc = DetectionDocumentInput(
        page_count=1,
        language="de",
        pages=(
            DetectionPageInput(page_number=1, width=595.0, height=842.0, tokens=tokens),
        ),
        acroform_widgets=tuple(widgets),
    )
    detected = LocalFieldDetectionProvider().detect(doc)
    choice_fields = [
        f for f in detected.fields if f.field_type in ("radio", "multiple_choice")
    ]
    labels = {f.label for f in choice_fields}
    assert "Aufenthaltsstatus" in labels
    assert "Familienstand" in labels


def test_horizontal_yes_no_rows_use_left_question_label() -> None:
    """Adjacent ja/nein pairs on the same row pick their own left-hand question
    instead of sharing a section header above."""
    widgets = [
        _checkbox("chkKueche1", "ja", 267.0, 213.0),
        _checkbox("chkKueche2", "nein", 304.0, 213.0),
        _checkbox("chkBad1", "ja", 439.0, 213.0),
        _checkbox("chkBad2", "nein", 479.0, 213.0),
    ]
    tokens = (
        _token("Zimmer", 70.0, 190.0),
        _token("Küche?", 225.0, 214.0),
        _token("[_]", 267.0, 213.0),
        _token("ja", 282.0, 214.0),
        _token("[_]", 304.0, 213.0),
        _token("nein", 319.0, 214.0),
        _token("Bad/Dusche?", 375.0, 214.0),
        _token("[_]", 439.0, 213.0),
        _token("ja", 454.0, 214.0),
        _token("[_]", 479.0, 213.0),
        _token("nein", 494.0, 214.0),
    )

    groups = group_checkbox_widgets(widgets, {1: tokens})
    assert len(groups) == 2
    assert groups[0].label == "Küche?"
    assert groups[1].label == "Bad/Dusche?"


def test_consecutive_yes_no_rows_never_merge_into_four_option_group() -> None:
    """Two stacked ja/nein rows (e.g. Row 1 outside repeated_sections + Row 2
    inside repeated_sections) must stay two separate ['ja', 'nein'] groups."""
    widgets = [
        _checkbox("chkJa1", "ja", 493.0, 668.0),
        _checkbox("chkNein1", "nein", 528.0, 668.0),
        _checkbox("chkJa2", "ja", 493.0, 692.0),
        _checkbox("chkNein2", "nein", 528.0, 692.0),
    ]
    rows = {"chkJa2": ("row", 1), "chkNein2": ("row", 1)}

    groups = group_checkbox_widgets(widgets, row_lookup=lambda name: rows.get(name))

    assert len(groups) == 2
    assert [o.label for o in groups[0].options] == ["ja", "nein"]
    assert [o.label for o in groups[1].options] == ["ja", "nein"]
