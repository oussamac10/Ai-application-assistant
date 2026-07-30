"""Notices, instructions and footers are not fields.

The French test form opens with "Attention : exemple non officiel. Utilisez
uniquement des données fictives." — a notice whose shape (short label, colon,
trailing text) is indistinguishable from a real field, so "Attention" became
question 1 with a Skip button that did nothing.

The filter refuses to decide on wording alone: rejecting a *real* field is
worse than keeping a spurious one, because a user can skip a bad question but
cannot answer one that was removed.
"""

from __future__ import annotations

import pytest

from app.field_detection.notices import (
    classify_non_field,
    filter_non_field_candidates,
    is_footer,
    is_instruction,
    is_notice_word,
    is_prose_value,
)
from app.field_detection.providers.base import BoundingBox, DetectedFieldCandidate


def _candidate(
    label: str,
    *,
    input_box: BoundingBox | None = None,
    options: tuple[str, ...] = (),
    existing_value: str | None = None,
) -> DetectedFieldCandidate:
    return DetectedFieldCandidate(
        candidate_key="c",
        page_number=1,
        label=label,
        normalized_name="c",
        field_type="text" if not options else "multiple_choice",
        confidence=0.8,
        source="native",
        input_bounding_box=input_box,
        options=options,
        existing_value=existing_value,
    )


@pytest.mark.parametrize(
    "label",
    [
        "Attention",
        "Warning",
        "Notice",
        "Important",
        "Achtung",
        "Hinweis",
        "Wichtig",
        "Avertissement",
        "Remarque",
        "تنبيه",
        "تحذير",
        "ملاحظة",
        "مهم",
    ],
)
def test_notice_headings_are_recognised(label: str) -> None:
    assert is_notice_word(label) is True


def test_a_notice_word_inside_a_sentence_is_not_a_notice_heading() -> None:
    """Only an (essentially) bare notice word counts."""
    assert is_notice_word("Attention à porter aux enfants du demandeur") is False


@pytest.mark.parametrize(
    "label",
    ["Attention", "Achtung", "تنبيه", "Avertissement"],
)
def test_notice_without_an_input_region_is_filtered(label: str) -> None:
    assert classify_non_field(_candidate(label)) == "warning"


def test_prose_after_the_label_is_not_an_existing_value() -> None:
    """The notice's own body text was being read as a pre-filled value, which
    made the notice look like a filled-in field."""
    candidate = _candidate(
        "Attention",
        existing_value="exemple non officiel. Utilisez uniquement des données fictives.",
    )
    assert classify_non_field(candidate) == "warning"


@pytest.mark.parametrize(
    "value,expected",
    [
        ("exemple non officiel. Utilisez uniquement des données.", True),
        ("A rather long run of words that is clearly a sentence body", True),
        ("Stuttgart", False),
        ("70188", False),
        (None, False),
    ],
)
def test_prose_value_detection(value: str | None, expected: bool) -> None:
    assert is_prose_value(value) is expected


# ---------------------------------------------------------------------------
# Layout evidence wins
# ---------------------------------------------------------------------------


def test_a_notice_word_with_an_input_region_is_kept() -> None:
    """The form drew somewhere to write, so it is a field whatever it is
    called."""
    candidate = _candidate(
        "Attention", input_box=BoundingBox(x=100, y=100, width=200, height=14)
    )
    assert classify_non_field(candidate) is None


def test_a_notice_word_with_options_is_kept() -> None:
    assert classify_non_field(_candidate("Important", options=("Yes", "No"))) is None


def test_a_notice_word_with_a_short_existing_value_is_kept() -> None:
    assert classify_non_field(_candidate("Note", existing_value="Stuttgart")) is None


# ---------------------------------------------------------------------------
# Instructions and footers
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label",
    [
        "Please complete every section",
        "Veuillez indiquer votre situation",
        "Bitte beachten Sie die Hinweise",
        "يرجى إدخال بيانات تجريبية",
    ],
)
def test_instructions_are_recognised(label: str) -> None:
    assert is_instruction(label) is True


def test_instruction_without_an_input_region_is_filtered() -> None:
    assert classify_non_field(_candidate("Please complete this form")) == "instruction"


@pytest.mark.parametrize(
    "label",
    ["Page 1 of 2", "page 1 sur 2", "Seite 2 von 3", "1 / 2"],
)
def test_footers_are_recognised(label: str) -> None:
    assert is_footer(label) is True


def test_footer_is_filtered() -> None:
    assert classify_non_field(_candidate("Page 1 of 2")) == "footer"


# ---------------------------------------------------------------------------
# Ordinary fields survive
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label",
    ["Nom de famille", "Code postal, ville", "Vermieter – Name", "اسم العائلة"],
)
def test_real_labels_are_never_filtered(label: str) -> None:
    assert classify_non_field(_candidate(label)) is None


def test_filter_reports_counts_and_keeps_the_rest() -> None:
    kept, counts = filter_non_field_candidates(
        [
            _candidate("Attention"),
            _candidate("Page 1 of 2"),
            _candidate("Please complete this form"),
            _candidate("Nom de famille"),
        ]
    )

    assert [c.label for c in kept] == ["Nom de famille"]
    assert counts.warning == 1
    assert counts.footer == 1
    assert counts.instruction == 1
    assert counts.total == 3


def test_filter_is_a_no_op_for_a_clean_document() -> None:
    candidates = [_candidate("Nom"), _candidate("Ville")]
    kept, counts = filter_non_field_candidates(candidates)

    assert kept == candidates
    assert counts.total == 0


def test_no_label_text_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level("DEBUG"):
        filter_non_field_candidates(
            [_candidate("Attention"), _candidate("Page 1 of 2")]
        )

    assert "Attention" not in caplog.text
    assert "warning_filtered=1" in caplog.text
