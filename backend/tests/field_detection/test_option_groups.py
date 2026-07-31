"""Selection-mark rows become one question, not one question per option.

The live failure: a French form's rows

    [_] Femme  [_] Homme  [_] Non-binaire  [_] Je préfère ne pas répondre
    [_] J'accepte la déclaration  [_] J'accepte le traitement des données

produced a free-text question per *option* — "Non-binaire", "Je préfère ne pas
répondre", "J'accepte la déclaration" — while the questions they belong to
("Gender", "Declarations") never existed.
"""

from __future__ import annotations

import pytest

from app.field_detection.labeling import LinePhrase, build_line_groups
from app.field_detection.option_groups import (
    _split_segment_at_markers,
    detect_option_groups,
    match_option_set,
    split_inline_option_row,
    strip_heading_number,
)
from app.field_detection.providers.base import BoundingBox, DetectionToken


def _token(text: str, x: float, y: float, width: float = 40.0):
    return DetectionToken(
        text=text,
        bounding_box=BoundingBox(x=x, y=y, width=width, height=12.0),
        source="native",
        confidence=1.0,
    )


def _option_row(y: float, labels: list[str], marker: str = "[_]"):
    """Builds one visual row of marker+label options, widely spaced so
    `split_line_into_segments` separates them."""
    tokens = []
    x = 40.0
    for label in labels:
        tokens.append(_token(marker, x, y, width=12.0))
        x += 22.0
        for word in label.split():
            tokens.append(_token(word, x, y, width=8.0 * len(word)))
            x += 8.0 * len(word) + 4.0
        x += 90.0  # a wide gap starts the next option's segment
    return tuple(tokens)


def _groups(rows: list[tuple], headings: dict[int, str] | None = None):
    line_groups = []
    for row in rows:
        line_groups.extend(build_line_groups(1, row))
    return detect_option_groups(1, line_groups, set(), headings or {})


# ---------------------------------------------------------------------------
# Grouping
# ---------------------------------------------------------------------------


def test_gender_row_becomes_one_single_choice_question() -> None:
    groups = _groups([_option_row(100, ["Femme", "Homme", "Non-binaire"])])

    assert len(groups) == 1
    group = groups[0]
    assert group.label == "Gender"
    assert group.field_type == "radio", "gender is exclusive"
    assert group.options == ("Femme", "Homme", "Non-binaire")
    assert group.label_source == "option_set"
    assert group.needs_review is False


def test_language_row_becomes_multiple_choice() -> None:
    """You may speak several languages, so the options are not exclusive."""
    groups = _groups([_option_row(100, ["Arabe", "Allemand", "Anglais"])])

    assert groups[0].field_type == "multiple_choice"
    assert groups[0].label == "Languages"


def test_employment_row_is_exclusive() -> None:
    groups = _groups([_option_row(100, ["Salarié(e)", "Étudiant(e)", "Retraité(e)"])])

    assert groups[0].field_type == "radio"
    assert groups[0].label == "Employment status"


def test_declaration_row_is_grouped_not_split() -> None:
    groups = _groups(
        [_option_row(100, ["J'accepte la déclaration", "J'accepte le traitement"])]
    )

    assert len(groups) == 1
    assert groups[0].label == "Declarations"
    assert groups[0].field_type == "multiple_choice"
    assert len(groups[0].options) == 2


def test_option_labels_never_become_standalone_questions() -> None:
    """The row is marked consumed, so later passes cannot claim its options."""
    row = _option_row(100, ["Femme", "Homme", "Non-binaire"])
    line_groups = build_line_groups(1, row)
    consumed: set[int] = set()

    detect_option_groups(1, line_groups, consumed, {})

    assert consumed == {0}, "the option row must be consumed"


def test_radio_glyphs_produce_a_single_choice_question() -> None:
    groups = _groups([_option_row(100, ["Alpha", "Beta", "Gamma"], marker="( )")])

    assert groups[0].field_type == "radio"


def test_unrecognised_checkbox_row_stays_multiple_choice() -> None:
    groups = _groups([_option_row(100, ["Alpha", "Beta", "Gamma"])])

    assert groups[0].field_type == "multiple_choice"


def test_unnamed_group_gets_a_neutral_label_and_review_flag() -> None:
    """Inventing a question is worse than admitting we do not know it."""
    groups = _groups([_option_row(100, ["Alpha", "Beta", "Gamma"])])

    assert groups[0].label == "Selection group"
    assert groups[0].label_source == "neutral"
    assert groups[0].needs_review is True
    assert groups[0].confidence < 0.6


def test_heading_names_an_unrecognised_group() -> None:
    groups = _groups(
        [_option_row(100, ["Alpha", "Beta"])],
        headings={0: "5. Documents joints"},
    )

    assert groups[0].label == "Documents joints"
    assert groups[0].label_source == "heading"
    assert groups[0].needs_review is False


def test_a_single_option_is_not_a_group() -> None:
    """One checkbox is a boolean, handled elsewhere — not a choice list."""
    assert _groups([_option_row(100, ["J'accepte"])]) == []


def test_a_row_mixing_options_and_prose_is_not_a_group() -> None:
    """Treating it as one would swallow whatever real field shares the line."""
    row = _option_row(100, ["Femme", "Homme"]) + (_token("Nom du demandeur", 700, 100),)
    assert _groups([row]) == []


def test_sentences_are_not_options() -> None:
    long_label = "Je certifie que toutes les informations fournies sont exactes."
    assert _groups([_option_row(100, [long_label, "Autre"])]) == []


def test_rows_are_separate_groups() -> None:
    """Two adjacent rows are two questions. A French form puts languages and
    contact channels on consecutive rows under one heading; merging them made
    a single seven-option question mixing the two."""
    groups = _groups(
        [
            _option_row(100, ["Français", "Allemand", "Anglais"]),
            _option_row(130, ["E-mail", "Téléphone", "Courrier postal"]),
        ]
    )

    assert len(groups) == 2
    assert groups[0].label == "Languages"
    assert groups[1].label == "Preferred contact method"


# ---------------------------------------------------------------------------
# Option-set matching
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "options,expected",
    [
        (("Male", "Female", "Non-binary"), "Gender"),
        (("Mann", "Frau", "Divers"), "Gender"),
        (("ذكر", "أنثى"), "Gender"),
        (("Arabic", "German", "English"), "Languages"),
        (("Ledig", "Verheiratet"), "Marital status"),
        (("Yes", "No"), "Yes or no"),
    ],
)
def test_recognised_sets_are_language_independent(
    options: tuple[str, ...], expected: str
) -> None:
    matched = match_option_set(options)
    assert matched is not None
    assert matched.label == expected


def test_one_coincidental_word_does_not_rename_a_group() -> None:
    """A majority of the row must match, so a stray "single" in a list of
    unrelated options cannot make it a marital-status question."""
    assert match_option_set(("Single", "Alpha", "Beta", "Gamma", "Delta")) is None


@pytest.mark.parametrize(
    "heading,expected",
    [
        ("5. Documents joints", "Documents joints"),
        ("2) Situation", "Situation"),
        ("§ 3 Mietraum", "Mietraum"),
        ("II. Angaben", "Angaben"),
        ("Documents", "Documents"),
    ],
)
def test_heading_numbering_is_stripped(heading: str, expected: str) -> None:
    assert strip_heading_number(heading) == expected


# ---------------------------------------------------------------------------
# Segment splitting (Phase 16 follow-up)
# ---------------------------------------------------------------------------


def test_a_segment_holding_two_markers_yields_two_options() -> None:
    """Segmentation is gap-based, so how many options land in one segment
    depends on how tightly the form spaced them.

    On the French test form the professional-status row segments as

        "(_) Salarie(e)" | "(_) Independant(e)" | "(_) Etudiant(e) (_) Demandeur d'emploi"

    because the gap before the fourth marker is narrower than the others.
    Requiring exactly one marker per segment rejected the whole row, so the
    group was never formed and all four options leaked as separate text
    questions. A marker is an unambiguous boundary: everything from one marker
    to the next is that marker's label, whatever the spacing.
    """
    segment = _phrase(
        [("(_)", 40), ("Etudiant(e)", 55), ("(_)", 130), ("Demandeur", 145)]
    )

    assert _split_segment_at_markers(segment) == [
        ("radio", "Etudiant(e)"),
        ("radio", "Demandeur"),
    ]


def test_a_segment_with_one_marker_is_unchanged() -> None:
    segment = _phrase([("(_)", 40), ("Femme", 55)])

    assert _split_segment_at_markers(segment) == [("radio", "Femme")]


def test_a_segment_with_no_marker_is_not_an_option() -> None:
    assert _split_segment_at_markers(_phrase([("Genre", 40)])) is None


def test_a_marker_with_no_label_after_it_is_rejected() -> None:
    """A trailing marker with nothing following it is layout, not an option."""
    assert _split_segment_at_markers(_phrase([("Femme", 40), ("(_)", 90)])) is None


def _phrase(parts: list[tuple[str, float]]) -> LinePhrase:
    """One line segment built from (text, x) pairs on a single row."""
    tokens = tuple(_token(text, x, 100.0, width=8.0 * len(text)) for text, x in parts)
    return LinePhrase(
        page_number=1,
        text=" ".join(text for text, _x in parts),
        tokens=tokens,
        bounding_box=BoundingBox(x=parts[0][1], y=100.0, width=400.0, height=12.0),
        source="native",
    )


# ---------------------------------------------------------------------------
# Inline option rows (question and options on one line)
# ---------------------------------------------------------------------------


def test_a_line_carrying_its_question_and_its_options_is_split() -> None:
    """The dominant shape in real government forms.

    The Stuttgart residence-permit application writes

        24 Wurde gegen Sie ... ein Ermittlungsverfahren eingeleitet? [_] ja [_] nein

    on one physical line. `_parse_option_row` requires every segment to begin
    with a marker, so it rejected these outright and every yes/no question
    leaked as free text. The rule is positional, not lexical: everything before
    the first marker is the question, everything from it onwards is the answer
    set.
    """
    line = _phrase(
        [
            ("24", 40),
            ("Wurde", 55),
            ("gegen", 90),
            ("Sie", 125),
            ("ein", 150),
            ("Ermittlungsverfahren", 175),
            ("eingeleitet?", 320),
            ("[_]", 400),
            ("ja", 415),
            ("[_]", 440),
            ("nein", 455),
        ]
    )

    result = split_inline_option_row([line])

    assert result is not None
    parent, options = result
    # The leading item number is stripped — it names the row, not the question.
    assert parent == "Wurde gegen Sie ein Ermittlungsverfahren eingeleitet?"
    assert options == [("checkbox", "ja"), ("checkbox", "nein")]


def test_the_inline_rule_is_language_independent() -> None:
    """No vocabulary is consulted, so `oui/non` and `نعم/لا` work for the same
    reason as `ja/nein` — and so does a set nobody anticipated."""
    for yes, no in (("oui", "non"), ("نعم", "لا"), ("yes", "no"), ("kyllä", "ei")):
        line = _phrase(
            [
                ("Avez", 40),
                ("vous", 70),
                ("un", 100),
                ("visa?", 120),
                ("[_]", 200),
                (yes, 215),
                ("[_]", 250),
                (no, 265),
            ]
        )
        result = split_inline_option_row([line])
        assert result is not None
        assert result[1] == [("checkbox", yes), ("checkbox", no)]


def test_a_row_that_starts_with_a_marker_is_left_to_the_plain_pass() -> None:
    """`_parse_option_row` already handles it, and handling it twice would
    invent a question out of the first option's label."""
    line = _phrase([("[_]", 40), ("ja", 55), ("[_]", 80), ("nein", 95)])

    assert split_inline_option_row([line]) is None


def test_too_little_leading_text_is_not_a_question() -> None:
    """ "ja [_] nein" reaches this pass when the first option's own marker did
    not render. Treating "ja" as the question would produce a nonsense group."""
    line = _phrase([("ja", 40), ("[_]", 60), ("nein", 80)])

    assert split_inline_option_row([line]) is None


def test_a_line_with_one_option_is_not_a_group() -> None:
    line = _phrase(
        [
            ("Haben", 40),
            ("Sie", 70),
            ("ein", 95),
            ("Visum?", 120),
            ("[_]", 200),
            ("ja", 215),
        ]
    )

    assert split_inline_option_row([line]) is None
