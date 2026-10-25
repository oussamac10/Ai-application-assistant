"""Requiredness comes from evidence, never from habit.

Every detected field previously defaulted to `required=True`, which blocked
users on fields the form never insisted on.
"""

from __future__ import annotations

import pytest

from app.field_detection.requiredness import (
    OPTIONAL,
    REQUIRED,
    UNKNOWN,
    detect_requiredness,
    document_requires_all,
    strip_required_marker,
    strip_requiredness_markers,
)


def test_acroform_flag_is_authoritative() -> None:
    """The document author set it explicitly; nothing outranks that."""
    assert detect_requiredness("Name", acroform_required=True).state == REQUIRED
    assert detect_requiredness("Name", acroform_required=False).state == OPTIONAL


def test_acroform_flag_beats_a_conflicting_label_marker() -> None:
    result = detect_requiredness("Name (optional)", acroform_required=True)
    assert result.state == REQUIRED
    assert result.evidence == "acroform_flag"


@pytest.mark.parametrize(
    "label",
    [
        "Full name *",
        "* Full name",
        "Nom complet ∗",
        "Full name (required)",
        "Full name (mandatory)",
        "Name (Pflichtfeld)",
        "Nom (obligatoire)",
        "Nom — champ obligatoire",
        "Nom (requis)",
        "Adresse (erforderlich)",
        "الاسم (مطلوب)",
        "الاسم (إلزامي)",
    ],
)
def test_required_markers_are_detected(label: str) -> None:
    assert detect_requiredness(label).state == REQUIRED


@pytest.mark.parametrize(
    "label",
    [
        "Middle name (optional)",
        "Zweiter Vorname (freiwillig)",
        "Deuxième prénom (facultatif)",
        "Autre langue (le cas échéant)",
        "اسم آخر (اختياري)",
    ],
)
def test_optional_markers_are_detected(label: str) -> None:
    assert detect_requiredness(label).state == OPTIONAL


def test_no_evidence_yields_unknown_not_required() -> None:
    """The bug this module exists for: silence is not consent."""
    result = detect_requiredness("Nom de l'employeur")
    assert result.state == UNKNOWN
    assert result.evidence == "no_evidence"
    assert result.is_required is False
    assert result.blocks_progress is False


@pytest.mark.parametrize(
    "label",
    [
        "Surname",
        "Nom de famille",
        "Nachname",
        "اسم العائلة",
        "Date of birth",
        "E-mail",
    ],
)
def test_semantic_importance_alone_never_produces_required(label: str) -> None:
    """A surname is obviously important, and a form is still free not to
    demand it. Importance is our opinion; requiredness is the document's."""
    assert detect_requiredness(label).state == UNKNOWN


def test_unknown_never_blocks_progress() -> None:
    assert detect_requiredness("Anything").blocks_progress is False


def test_form_level_statement_makes_unmarked_fields_required() -> None:
    result = detect_requiredness("Name", all_fields_required=True)
    assert result.state == REQUIRED
    assert result.evidence == "form_statement"


def test_an_explicit_optional_marker_beats_the_form_level_statement() -> None:
    """The specific beats the general."""
    result = detect_requiredness("Note (optional)", all_fields_required=True)
    assert result.state == OPTIONAL


def test_adjacent_text_is_considered() -> None:
    assert detect_requiredness("Name", adjacent_text="Pflichtfeld").state == REQUIRED


def test_an_asterisk_must_be_trailing() -> None:
    """A footnote reference mid-sentence is not a required marker."""
    assert detect_requiredness("See note * for details").state == UNKNOWN
    assert detect_requiredness("Name *").state == REQUIRED


@pytest.mark.parametrize(
    "text,expected",
    [
        ("All fields are required.", True),
        ("Alle Felder sind Pflichtfelder", True),
        ("Tous les champs sont obligatoires", True),
        ("جميع الحقول إلزامية", True),
        ("Please complete the form.", False),
        (None, False),
    ],
)
def test_form_level_statement_detection(text: str | None, expected: bool) -> None:
    assert document_requires_all(text) is expected


def test_marker_is_stripped_from_the_displayed_label() -> None:
    assert strip_required_marker("Full name *") == "Full name"
    assert strip_required_marker("Full name") == "Full name"


def test_evidence_and_confidence_are_recorded() -> None:
    """An admin override needs to know what the decision was based on."""
    result = detect_requiredness("Name *")
    assert result.evidence == "asterisk"
    assert 0.0 < result.confidence <= 1.0


@pytest.mark.parametrize(
    "raw_label,expected_clean",
    [
        ("Vorname *:", "Vorname"),
        ("Geburtsdatum (TT.MM.JJJJ) *:", "Geburtsdatum (TT.MM.JJJJ)"),
        ("Nom (*):", "Nom"),
        ("First name *", "First name"),
    ],
)
def test_trailing_asterisk_before_colon_is_detected_and_stripped(
    raw_label: str, expected_clean: str
) -> None:
    assert detect_requiredness(raw_label).state == REQUIRED
    assert strip_requiredness_markers(raw_label) == expected_clean
