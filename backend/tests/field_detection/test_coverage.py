"""Coverage: what the document offered versus what came back.

The defect this exists for, measured on the real file: the local pass produced
**5** candidates for `required_optional_validation_test_form.pdf`, a two-page
form carrying about thirty fields. Every one of the five was flawless — good
label, real input region, high confidence — so `score_extraction` returned
**0.83**, comfortably above the 0.55 escalation threshold, and the document was
never sent to a provider that could read it. The user saw five questions.

A score computed only from the output cannot see what the output is missing.
These tests pin the second question.
"""

from __future__ import annotations

import pytest

from app.field_detection.coverage import (
    LOW_LABEL_COVERAGE,
    POOR_PAGE_COVERAGE,
    UNCLAIMED_SELECTION_MARKS,
    looks_like_a_label,
    measure_coverage,
)
from app.field_detection.providers.base import (
    BoundingBox,
    DetectedFieldCandidate,
    DetectionDocumentInput,
    DetectionPageInput,
    DetectionToken,
)


def _token(text: str, x: float, y: float) -> DetectionToken:
    return DetectionToken(
        text=text,
        confidence=1.0,
        bounding_box=BoundingBox(x=x, y=y, width=len(text) * 5.0, height=10.0),
        source="native",
    )


def _label_line(text: str, y: float) -> list[DetectionToken]:
    """One visual line, laid out left to right."""
    tokens = []
    x = 40.0
    for word in text.split():
        tokens.append(_token(word, x, y))
        x += len(word) * 5.0 + 4.0
    return tokens


def _page(
    number: int, lines: list[str], marks: int = 0, mark_y: float = 500.0
) -> DetectionPageInput:
    tokens: list[DetectionToken] = []
    for index, line in enumerate(lines):
        tokens.extend(_label_line(line, 100.0 + index * 30.0))
    for index in range(marks):
        tokens.append(_token("(_)", 40.0 + index * 60.0, mark_y))
    return DetectionPageInput(
        page_number=number, width=612.0, height=792.0, tokens=tuple(tokens)
    )


def _candidate(index: int, page: int = 1, options: tuple[str, ...] = ()):
    return DetectedFieldCandidate(
        candidate_key=f"c{index}",
        page_number=page,
        label=f"Question {index}",
        normalized_name=f"field_{index}",
        field_type="text",
        confidence=0.9,
        source="native",
        input_bounding_box=BoundingBox(10.0, 10.0, 100.0, 20.0),
        options=options,
    )


def _document(pages: list[DetectionPageInput]) -> DetectionDocumentInput:
    return DetectionDocumentInput(page_count=len(pages), pages=tuple(pages))


# ---------------------------------------------------------------------------
# What counts as a label line
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Nom de famille *", True),
        ("Deuxieme prenom (Optional)", True),
        ("Date de naissance:", True),
        ("الاسم *", True),
        ("Nachname:", True),
        ("Date de debut d'emploi (Optional)", True),
        # Not labels.
        ("Nom de famille", False),
        ("", False),
        ("*", False),
        (
            "Die Angaben werden gemaess Artikel 6 Absatz 1 der Verordnung "
            "verarbeitet und nur zu diesem Zweck gespeichert:",
            False,
        ),
    ],
)
def test_label_line_recognition(text: str, expected: bool) -> None:
    """Punctuation and markers only — no vocabulary, so it behaves the same in
    every language and on documents nobody anticipated."""
    assert looks_like_a_label(text) is expected


# ---------------------------------------------------------------------------
# The reported defect
# ---------------------------------------------------------------------------


def test_finding_a_fraction_of_the_labels_is_reported_as_a_gap() -> None:
    """Five candidates against seventeen label lines. The per-candidate score
    cannot see this; coverage must."""
    document = _document([_page(1, [f"Champ numero {n} *" for n in range(17)])])
    candidates = tuple(_candidate(i) for i in range(5))

    coverage = measure_coverage(document, candidates)

    assert coverage.label_line_count == 17
    assert coverage.label_coverage < 0.35
    assert coverage.weakest_signal() == LOW_LABEL_COVERAGE


def test_finding_every_label_reports_no_gap() -> None:
    document = _document([_page(1, [f"Champ numero {n} *" for n in range(6)])])
    candidates = tuple(_candidate(i) for i in range(6))

    coverage = measure_coverage(document, candidates)

    assert coverage.label_coverage == 1.0
    assert coverage.weakest_signal() is None


def test_selection_marks_left_unclaimed_are_reported() -> None:
    """Marks that reached no candidate's option list are options that leaked,
    or a group that was never formed — the Stuttgart form's yes/no rows."""
    document = _document([_page(1, ["Mit Visum eingereist:"], marks=12)])
    candidates = (_candidate(0),)

    coverage = measure_coverage(document, candidates)

    assert coverage.selection_mark_count == 12
    assert coverage.unclaimed_selection_marks == 12
    assert coverage.mark_coverage == 0.0
    assert coverage.weakest_signal() == UNCLAIMED_SELECTION_MARKS


def test_marks_folded_into_a_group_count_as_claimed() -> None:
    document = _document([_page(1, ["Genre:"], marks=4)])
    candidates = (_candidate(0, options=("Femme", "Homme", "Non-binaire", "Autre")),)

    coverage = measure_coverage(document, candidates)

    assert coverage.unclaimed_selection_marks == 0
    assert coverage.mark_coverage == 1.0


def test_a_page_that_offered_fields_but_produced_none_is_a_gap() -> None:
    document = _document(
        [_page(1, ["Nom *", "Prenom *"]), _page(2, ["Adresse *", "Ville *"])]
    )
    candidates = (_candidate(0, page=1), _candidate(1, page=1))

    coverage = measure_coverage(document, candidates)

    assert coverage.page_coverage == 0.5
    assert coverage.weakest_signal() == POOR_PAGE_COVERAGE


# ---------------------------------------------------------------------------
# No evidence is not evidence of a gap
# ---------------------------------------------------------------------------


def test_a_signature_page_with_no_fields_is_not_counted_against_coverage() -> None:
    """The reference German rental contract is three pages with fields on two;
    the third is a signature block. Counting it as a miss would escalate a
    document that was read perfectly."""
    document = _document(
        [
            _page(1, ["Vermieter *", "Mieter *"]),
            _page(2, ["Mietbeginn *"]),
            _page(3, ["Ort und Unterschrift des Vermieters"]),  # no marker
        ]
    )
    candidates = (
        _candidate(0, page=1),
        _candidate(1, page=1),
        _candidate(2, page=2),
    )

    coverage = measure_coverage(document, candidates)

    assert coverage.page_coverage == 1.0
    assert coverage.weakest_signal() is None


def test_a_document_with_no_punctuation_evidence_reports_full_coverage() -> None:
    """A form whose lines carry no markers gives the heuristic nothing to work
    with. Reporting a gap there would escalate every such document."""
    document = _document([_page(1, ["Nom de famille", "Prenom", "Adresse"])])

    coverage = measure_coverage(document, ())

    assert coverage.label_coverage == 1.0
    assert coverage.mark_coverage == 1.0
    assert coverage.page_coverage == 1.0
    assert coverage.weakest_signal() is None


def test_coverage_never_exceeds_one() -> None:
    """An extractor that finds more than the heuristic counted is doing well,
    not suspiciously well, and must not outscore perfect coverage."""
    document = _document([_page(1, ["Nom *"], marks=2)])
    candidates = tuple(_candidate(i, options=("a", "b", "c", "d")) for i in range(10))

    coverage = measure_coverage(document, candidates)

    assert coverage.label_coverage == 1.0
    assert coverage.mark_coverage == 1.0
    assert coverage.unclaimed_selection_marks == 0


def test_coverage_is_deterministic() -> None:
    """It decides whether a paid service is called."""
    document = _document([_page(1, ["Nom *", "Prenom *"], marks=3)])
    candidates = (_candidate(0), _candidate(1))

    assert measure_coverage(document, candidates) == measure_coverage(
        document, candidates
    )
