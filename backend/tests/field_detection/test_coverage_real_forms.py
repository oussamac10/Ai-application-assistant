"""Coverage measured on the real documents that exposed the defect.

Synthetic pages can be made to say anything. These run the actual local
extractor over committed PDFs, so the numbers here are the ones the router will
see in production, and a regression that would silently start billing (or stop
escalating a document the user cannot use) fails in CI.

`required-optional-validation-fr.pdf` is the reported French form. The
Stuttgart residence-permit PDF is not committed — it is a real government
document — so its behaviour is covered by the encrypted-PDF tests and by the
synthetic mark-coverage cases in `test_coverage.py`.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import settings
from app.field_detection.coverage import LOW_LABEL_COVERAGE, measure_coverage
from app.field_detection.extraction import extract_native_document_input
from app.field_detection.providers.local import LocalFieldDetectionProvider
from app.field_detection.quality import score_extraction

_FIXTURES = Path(__file__).resolve().parents[3] / "fixtures" / "pdf"
_FRENCH_FORM = _FIXTURES / "required-optional-validation-fr.pdf"
_RENTAL_CONTRACT = _FIXTURES / "rental-contract-de.pdf"


def _analyse(pdf: Path):
    if not pdf.exists():
        pytest.skip(f"Fixture PDF not found: {pdf.name}")
    document = extract_native_document_input(pdf)
    result = LocalFieldDetectionProvider().detect(document)
    return document, result, measure_coverage(document, result.fields)


def test_the_french_form_is_scored_well_but_covered_badly() -> None:
    """The exact shape of the reported defect, on the real file.

    Five candidates for a two-page form of about thirty fields. Each of the
    five is flawless, so the per-candidate score is high — and that is
    precisely why coverage had to exist.
    """
    _document, result, coverage = _analyse(_FRENCH_FORM)
    quality = score_extraction(result.fields)

    # The score alone would have left this document unescalated.
    assert quality.score >= settings.HYBRID_LOCAL_QUALITY_THRESHOLD

    # Coverage sees what the score cannot.
    assert coverage.label_line_count >= 15
    assert coverage.label_coverage < settings.HYBRID_MIN_LABEL_COVERAGE
    assert coverage.weakest_signal() == LOW_LABEL_COVERAGE


def test_the_french_form_selection_marks_are_real() -> None:
    """The gender / professional-status / languages options are drawn vector
    squares, not text glyphs — the reason a purely textual pass never saw
    them as a group."""
    _document, _result, coverage = _analyse(_FRENCH_FORM)

    assert coverage.selection_mark_count >= 20


def test_the_reference_rental_contract_still_reports_full_coverage() -> None:
    """The document that must stay free. Three pages with fields on two: the
    third is a signature block, and counting it as a miss would start billing
    every upload of a document that was read perfectly.
    """
    _document, _result, coverage = _analyse(_RENTAL_CONTRACT)

    assert coverage.label_coverage == 1.0
    assert coverage.mark_coverage == 1.0
    assert coverage.page_coverage == 1.0
    assert coverage.weakest_signal() is None
