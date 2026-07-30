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

from app.field_detection.labeling import build_line_groups
from app.field_detection.option_groups import (
    detect_option_groups,
    match_option_set,
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
