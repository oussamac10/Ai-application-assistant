"""Deterministic confidence-routing tests (Phase 13).

No AI/Ollama is involved in this decision — every case here is exercised
purely against `app/core/config.py` thresholds, so results must be
reproducible and independent of any provider.
"""

from collections.abc import Generator

import pytest

from app.core.config import settings
from app.field_detection.confidence import decide_auto_review_status
from app.field_detection.providers.base import DetectedFieldCandidate


@pytest.fixture(autouse=True)
def fixed_thresholds() -> Generator[None, None, None]:
    original_auto = settings.FIELD_AUTO_CONFIRM_THRESHOLD
    original_clarify = settings.FIELD_CLARIFICATION_THRESHOLD
    settings.FIELD_AUTO_CONFIRM_THRESHOLD = 0.75
    settings.FIELD_CLARIFICATION_THRESHOLD = 0.4
    yield
    settings.FIELD_AUTO_CONFIRM_THRESHOLD = original_auto
    settings.FIELD_CLARIFICATION_THRESHOLD = original_clarify


def _candidate(**overrides: object) -> DetectedFieldCandidate:
    defaults: dict[str, object] = {
        "candidate_key": "k1",
        "page_number": 1,
        "label": "Email",
        "normalized_name": "email",
        "field_type": "email",
        "confidence": 0.9,
        "source": "native",
    }
    defaults.update(overrides)
    return DetectedFieldCandidate(**defaults)  # type: ignore[arg-type]


def test_high_confidence_field_is_auto_confirmed() -> None:
    candidate = _candidate(confidence=0.9, field_type="email")
    assert decide_auto_review_status(candidate) == "confirmed"


def test_confidence_exactly_at_auto_confirm_threshold_is_confirmed() -> None:
    candidate = _candidate(confidence=0.75, field_type="text")
    assert decide_auto_review_status(candidate) == "confirmed"


def test_medium_confidence_field_is_pending_review_not_confirmed() -> None:
    candidate = _candidate(confidence=0.5, field_type="text")
    assert decide_auto_review_status(candidate) == "pending_review"


def test_low_confidence_field_needs_clarification() -> None:
    candidate = _candidate(confidence=0.2, field_type="text")
    assert decide_auto_review_status(candidate) == "needs_clarification"


def test_unknown_type_never_auto_confirmed_regardless_of_confidence() -> None:
    candidate = _candidate(confidence=0.99, field_type="unknown")
    assert decide_auto_review_status(candidate) == "needs_clarification"


def test_choice_field_without_options_needs_clarification() -> None:
    candidate = _candidate(confidence=0.95, field_type="radio", options=())
    assert decide_auto_review_status(candidate) == "needs_clarification"


def test_choice_field_with_options_can_be_auto_confirmed() -> None:
    candidate = _candidate(confidence=0.95, field_type="radio", options=("Yes", "No"))
    assert decide_auto_review_status(candidate) == "confirmed"


def test_multiple_choice_without_options_needs_clarification() -> None:
    candidate = _candidate(confidence=0.9, field_type="multiple_choice", options=())
    assert decide_auto_review_status(candidate) == "needs_clarification"


def test_checkbox_high_confidence_auto_confirmed() -> None:
    candidate = _candidate(confidence=0.97, field_type="checkbox")
    assert decide_auto_review_status(candidate) == "confirmed"


def test_multiline_text_high_confidence_auto_confirmed() -> None:
    candidate = _candidate(confidence=0.8, field_type="multiline_text")
    assert decide_auto_review_status(candidate) == "confirmed"
