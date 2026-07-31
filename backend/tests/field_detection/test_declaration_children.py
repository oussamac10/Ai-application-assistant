"""A declaration block is not one question.

The French test form ends with:

    [_] Je certifie que les informations sont exactes *
    [_] J'accepte le traitement des donnees de test *
    [_] Je souhaite recevoir des nouvelles (Optional)

Detection folded all three into one `multiple_choice`, which turns them into
"tick any of these" — the two mandatory consents silently stopped being
mandatory, and the frontend offered a global Skip over the whole block. That is
the one thing a declaration block exists to prevent.

The trigger is structural, not vocabulary: **an option carrying its own
requiredness marker cannot be an option**, because a choice question's
requiredness belongs to the question rather than to individual answers. So this
fires on any such block in any language, while an ordinary unmarked checkbox
list stays a single multiple_choice.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.field_detection.extraction import extract_native_document_input
from app.field_detection.option_groups import independent_boolean_options
from app.field_detection.providers.local import LocalFieldDetectionProvider
from app.field_detection.requiredness import strip_requiredness_markers

_FRENCH_FORM = (
    Path(__file__).resolve().parents[3]
    / "fixtures"
    / "pdf"
    / "required-optional-validation-fr.pdf"
)


# ---------------------------------------------------------------------------
# The structural rule
# ---------------------------------------------------------------------------


def test_options_carrying_their_own_markers_become_independent_booleans() -> None:
    result = independent_boolean_options(
        (
            "Je certifie que les informations sont exactes *",
            "J'accepte le traitement des donnees de test *",
            "Je souhaite recevoir des nouvelles (Optional)",
        )
    )

    assert result == (
        ("Je certifie que les informations sont exactes", "required"),
        ("J'accepte le traitement des donnees de test", "required"),
        ("Je souhaite recevoir des nouvelles", "optional"),
    )


def test_an_ordinary_checkbox_list_stays_one_question() -> None:
    """ "Documents joints" is six unmarked checkboxes — a real multiple_choice,
    and it must not be shattered into six questions."""
    assert (
        independent_boolean_options(
            (
                "Curriculum vitae",
                "Devis de formation",
                "Justificatif de revenus",
                "Piece d'identite",
            )
        )
        is None
    )


def test_the_rule_is_not_tied_to_declaration_wording() -> None:
    """No vocabulary is consulted, so an unanticipated block in an
    unanticipated language behaves the same way."""
    assert independent_boolean_options(
        ("Ich bestaetige die Angaben *", "Newsletter erwuenscht (Freiwillig)")
    ) == (
        ("Ich bestaetige die Angaben", "required"),
        ("Newsletter erwuenscht", "optional"),
    )
    assert independent_boolean_options(
        ("أوافق على المعالجة *", "النشرة (اختياري)")
    ) == (
        ("أوافق على المعالجة", "required"),
        ("النشرة", "optional"),
    )


def test_one_marked_option_is_enough_to_split_the_block() -> None:
    """A block where only some children are mandatory is still a block of
    independent answers — the unmarked ones simply have no evidence."""
    result = independent_boolean_options(("I certify this is true *", "Send me news"))

    assert result == (
        ("I certify this is true", "required"),
        ("Send me news", "unknown"),
    )


# ---------------------------------------------------------------------------
# Display labels
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("Methode de contact preferee *", "Methode de contact preferee"),
        ("Langues preferees (Optional)", "Langues preferees"),
        ("Deuxieme prenom (Optional)", "Deuxieme prenom"),
        ("Zweiter Vorname (Freiwillig)", "Zweiter Vorname"),
        ("اسم آخر (اختياري)", "اسم آخر"),
        # Nothing to strip.
        ("Nom de famille", "Nom de famille"),
        # "Facultatif" as an actual label survives — only a bracketed trailing
        # marker is metadata.
        ("Facultatif", "Facultatif"),
    ],
)
def test_requiredness_markers_are_stripped_from_display_labels(
    raw: str, expected: str
) -> None:
    """The frontend renders requiredness itself from the resolved state.
    Leaving the marker in shows it twice — and shows it in the document's
    language inside an interface in another one."""
    assert strip_requiredness_markers(raw) == expected


# ---------------------------------------------------------------------------
# End to end on the real form
# ---------------------------------------------------------------------------


def test_the_french_form_declarations_are_three_independent_booleans() -> None:
    if not _FRENCH_FORM.exists():
        pytest.skip(f"Fixture PDF not found: {_FRENCH_FORM.name}")

    document = extract_native_document_input(_FRENCH_FORM)
    fields = LocalFieldDetectionProvider().detect(document).fields

    declarations = [
        f for f in fields if f.label.startswith(("Je certifie", "J'accepte", "Je souh"))
    ]
    assert len(declarations) == 3

    by_label = {f.label: f for f in declarations}
    assert by_label["Je certifie que les informations sont exactes"].required is True
    assert by_label["J'accepte le traitement des donnees de test"].required is True
    assert by_label["Je souhaite recevoir des nouvelles"].required is False

    # Each is its own boolean question, never an option of a shared one.
    for field in declarations:
        assert field.field_type == "checkbox"
        assert field.options == ()

    # And no combined declaration question survives alongside them.
    assert not any(
        f.field_type in ("multiple_choice", "radio")
        and any("certifie" in option for option in f.options)
        for f in fields
    )


def test_the_french_form_document_checklist_stays_one_question() -> None:
    if not _FRENCH_FORM.exists():
        pytest.skip(f"Fixture PDF not found: {_FRENCH_FORM.name}")

    document = extract_native_document_input(_FRENCH_FORM)
    fields = LocalFieldDetectionProvider().detect(document).fields

    checklist = [f for f in fields if "documents fournis" in f.label]
    assert len(checklist) == 1
    assert checklist[0].field_type == "multiple_choice"
    assert len(checklist[0].options) == 6


def test_group_labels_carry_their_own_requiredness() -> None:
    if not _FRENCH_FORM.exists():
        pytest.skip(f"Fixture PDF not found: {_FRENCH_FORM.name}")

    document = extract_native_document_input(_FRENCH_FORM)
    by_label = {
        f.label: f for f in LocalFieldDetectionProvider().detect(document).fields
    }

    # "Methode de contact preferee *" -> required, marker stripped.
    assert by_label["Methode de contact preferee"].required is True
    # "Langues preferees (Optional)" -> optional, marker stripped.
    assert by_label["Langues preferees"].required is False
    # "Genre" carries no marker at all and must stay undecided.
    assert by_label["Genre"].required is None
