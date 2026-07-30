"""Local-first routing: when Azure is called, and when it is not.

The rule under test is a cost rule as much as a correctness one. A hosted call
must happen when the local pass genuinely failed to read a document, must not
happen when it succeeded, and must never be able to make the outcome *worse*
than not calling at all.

No test here touches a live service: the Azure side is a stub, per
`docs/claude/domain-rules.md` ("automated tests must never call a live/paid
provider").
"""

from __future__ import annotations

from collections.abc import Generator

import pytest

from app.core.config import settings
from app.field_detection.providers.base import (
    BoundingBox,
    DetectedFieldCandidate,
    DetectionDocumentInput,
    DetectionPageInput,
    DetectionResult,
)
from app.field_detection.providers.hybrid import (
    REASON_AZURE_FAILED,
    REASON_AZURE_NOT_BETTER,
    REASON_AZURE_NOT_CONFIGURED,
    REASON_ESCALATED,
    REASON_LOCAL_SUFFICIENT,
    REASON_PAGE_LIMIT,
    HybridFieldDetectionProvider,
)
from app.field_detection.quality import (
    ExtractionQuality,
    is_meaningful_label,
    score_extraction,
)


def _candidate(index: int, label: str = "Nom de famille", *, with_input: bool = True):
    return DetectedFieldCandidate(
        candidate_key=f"c{index}",
        page_number=1,
        label=label,
        normalized_name=f"field_{index}",
        field_type="text",
        confidence=0.8,
        source="native",
        input_bounding_box=BoundingBox(10.0, 10.0, 100.0, 20.0) if with_input else None,
    )


def _good_fields(count: int = 10) -> tuple[DetectedFieldCandidate, ...]:
    return tuple(_candidate(i, f"Question {i} label") for i in range(count))


def _poor_fields() -> tuple[DetectedFieldCandidate, ...]:
    """What a failed read looks like: two candidates, placeholder labels, no
    input regions. Modelled on the Arabic form that collapsed 27 candidates."""
    return (
        _candidate(0, "1.", with_input=False),
        _candidate(1, "-", with_input=False),
    )


class _StubProvider:
    """A provider that answers with whatever it was given, or raises."""

    def __init__(self, name: str, fields=(), error: Exception | None = None) -> None:
        self.provider_name = name
        self.provider_version = "test"
        self._fields = fields
        self._error = error
        self.calls = 0

    def detect(self, document: DetectionDocumentInput) -> DetectionResult:
        self.calls += 1
        if self._error is not None:
            raise self._error
        return DetectionResult(self.provider_name, self.provider_version, self._fields)


def _document(page_count: int = 1) -> DetectionDocumentInput:
    return DetectionDocumentInput(
        page_count=page_count,
        pages=tuple(
            DetectionPageInput(page_number=n + 1, width=612.0, height=792.0)
            for n in range(page_count)
        ),
    )


@pytest.fixture(autouse=True)
def restore_settings() -> Generator[None, None, None]:
    original = (
        settings.HYBRID_LOCAL_QUALITY_THRESHOLD,
        settings.HYBRID_MAX_ESCALATION_PAGES,
        settings.AZURE_DOCUMENT_INTELLIGENCE_ENABLED,
        settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
        settings.AZURE_DOCUMENT_INTELLIGENCE_API_KEY,
    )
    yield
    (
        settings.HYBRID_LOCAL_QUALITY_THRESHOLD,
        settings.HYBRID_MAX_ESCALATION_PAGES,
        settings.AZURE_DOCUMENT_INTELLIGENCE_ENABLED,
        settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT,
        settings.AZURE_DOCUMENT_INTELLIGENCE_API_KEY,
    ) = original


# ---------------------------------------------------------------------------
# The quality score
# ---------------------------------------------------------------------------


def test_a_well_read_document_scores_above_the_default_threshold() -> None:
    quality = score_extraction(_good_fields())

    assert quality.score >= settings.HYBRID_LOCAL_QUALITY_THRESHOLD
    assert quality.field_count == 10
    assert quality.label_quality == 1.0


def test_a_failed_read_scores_below_the_default_threshold() -> None:
    quality = score_extraction(_poor_fields())

    assert quality.score < settings.HYBRID_LOCAL_QUALITY_THRESHOLD
    assert quality.label_quality == 0.0


def test_an_empty_result_scores_zero() -> None:
    assert score_extraction(()).score == 0.0


def test_the_score_is_deterministic() -> None:
    """It decides whether money is spent, so the same input must always give
    the same answer."""
    fields = _good_fields()

    assert score_extraction(fields) == score_extraction(fields)


@pytest.mark.parametrize(
    "label,expected",
    [
        ("Nom de famille", True),
        ("اسم العائلة", True),
        ("Straße", True),
        ("1.", False),
        ("-", False),
        ("  ", False),
        ("", False),
        (None, False),
        ("12", False),
    ],
)
def test_meaningful_label_detection(label: str | None, expected: bool) -> None:
    assert is_meaningful_label(label) is expected


def test_a_short_form_is_not_punished_for_its_length_alone() -> None:
    """Eight well-labelled fields is a real short form, not a failed read."""
    quality = score_extraction(_good_fields(8))

    assert quality.score >= settings.HYBRID_LOCAL_QUALITY_THRESHOLD


def test_the_weakest_signal_is_reported_for_diagnostics() -> None:
    quality = ExtractionQuality(
        score=0.3,
        field_count=20,
        label_quality=0.1,
        input_evidence=0.9,
        mean_confidence=0.8,
    )

    assert quality.weakest_signal() == "low_label_quality"


# ---------------------------------------------------------------------------
# Routing
# ---------------------------------------------------------------------------


def test_a_good_local_result_never_calls_azure() -> None:
    """The whole point: an ordinary digital form costs nothing."""
    local = _StubProvider("local", _good_fields())
    azure = _StubProvider("azure", _good_fields(30))
    provider = HybridFieldDetectionProvider(local, azure)

    result = provider.detect(_document())

    assert azure.calls == 0
    assert result.provider_name == "local"
    assert provider.last_decision is not None
    assert provider.last_decision.reason == REASON_LOCAL_SUFFICIENT
    assert provider.last_decision.escalated is False


def test_a_poor_local_result_escalates_and_serves_azure() -> None:
    local = _StubProvider("local", _poor_fields())
    azure = _StubProvider("azure", _good_fields(20))
    provider = HybridFieldDetectionProvider(local, azure)

    result = provider.detect(_document())

    assert azure.calls == 1
    assert result.provider_name == "azure"
    assert len(result.fields) == 20
    assert provider.last_decision is not None
    assert provider.last_decision.reason == REASON_ESCALATED
    assert provider.last_decision.escalated is True


def test_the_local_pass_always_runs_first() -> None:
    """Local-first is not "try Azure and fall back" — the free provider is
    always the one that answers unless it demonstrably failed."""
    local = _StubProvider("local", _poor_fields())
    azure = _StubProvider("azure", _good_fields(20))

    HybridFieldDetectionProvider(local, azure).detect(_document())

    assert local.calls == 1


def test_an_azure_failure_degrades_to_the_local_result() -> None:
    """A hybrid provider that can fail where the local one would have
    succeeded is a downgrade, not a feature."""
    local = _StubProvider("local", _poor_fields())
    azure = _StubProvider("azure", error=RuntimeError("boom"))
    provider = HybridFieldDetectionProvider(local, azure)

    result = provider.detect(_document())

    assert result.provider_name == "local"
    assert result.fields == _poor_fields()
    assert provider.last_decision is not None
    assert provider.last_decision.reason == REASON_AZURE_FAILED


def test_a_worse_azure_result_is_discarded() -> None:
    """Paying for a worse answer is the one outcome with no upside."""
    local = _StubProvider("local", _poor_fields())
    azure = _StubProvider("azure", ())
    provider = HybridFieldDetectionProvider(local, azure)

    result = provider.detect(_document())

    assert result.provider_name == "local"
    assert provider.last_decision is not None
    assert provider.last_decision.reason == REASON_AZURE_NOT_BETTER


def test_a_document_over_the_page_limit_is_never_escalated() -> None:
    settings.HYBRID_MAX_ESCALATION_PAGES = 5
    local = _StubProvider("local", _poor_fields())
    azure = _StubProvider("azure", _good_fields(30))
    provider = HybridFieldDetectionProvider(local, azure)

    result = provider.detect(_document(page_count=6))

    assert azure.calls == 0
    assert result.provider_name == "local"
    assert provider.last_decision is not None
    assert provider.last_decision.reason == REASON_PAGE_LIMIT


def test_the_page_limit_is_reported_ahead_of_poor_quality() -> None:
    """An operator needs to know the document was blocked by the limit, not
    merely that it read badly."""
    settings.HYBRID_MAX_ESCALATION_PAGES = 1
    provider = HybridFieldDetectionProvider(
        _StubProvider("local", _poor_fields()), _StubProvider("azure", _good_fields())
    )

    provider.detect(_document(page_count=99))

    assert provider.last_decision is not None
    assert provider.last_decision.reason == REASON_PAGE_LIMIT


def test_a_good_local_result_is_served_even_over_the_page_limit() -> None:
    settings.HYBRID_MAX_ESCALATION_PAGES = 1
    azure = _StubProvider("azure", _good_fields(30))
    provider = HybridFieldDetectionProvider(
        _StubProvider("local", _good_fields()), azure
    )

    provider.detect(_document(page_count=50))

    assert azure.calls == 0
    assert provider.last_decision is not None
    assert provider.last_decision.reason == REASON_LOCAL_SUFFICIENT


def test_without_azure_configured_a_poor_document_still_returns_local_fields() -> None:
    """The cheap default must be deployable with no paid account at all."""
    settings.AZURE_DOCUMENT_INTELLIGENCE_ENABLED = False
    settings.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT = None
    settings.AZURE_DOCUMENT_INTELLIGENCE_API_KEY = None
    provider = HybridFieldDetectionProvider(_StubProvider("local", _poor_fields()))

    result = provider.detect(_document())

    assert result.provider_name == "local"
    assert provider.last_decision is not None
    assert provider.last_decision.reason == REASON_AZURE_NOT_CONFIGURED


def test_the_threshold_is_the_only_thing_deciding_escalation() -> None:
    """Raising the threshold escalates a document that previously passed —
    the decision is arithmetic on a setting, with nothing else involved."""
    local = _StubProvider("local", _good_fields())
    azure = _StubProvider("azure", _good_fields(40))

    settings.HYBRID_LOCAL_QUALITY_THRESHOLD = 0.1
    HybridFieldDetectionProvider(local, azure).detect(_document())
    assert azure.calls == 0

    settings.HYBRID_LOCAL_QUALITY_THRESHOLD = 0.99
    HybridFieldDetectionProvider(local, azure).detect(_document())
    assert azure.calls == 1


# ---------------------------------------------------------------------------
# Cost accounting
# ---------------------------------------------------------------------------


def test_no_azure_diagnostics_are_reported_when_the_local_pass_answered() -> None:
    """Usage is recorded from these; reporting a stale Azure call would
    overstate cost on a document that never made one."""
    azure = _StubProvider("azure", _good_fields(30))
    azure.last_diagnostics = object()  # type: ignore[attr-defined]
    provider = HybridFieldDetectionProvider(
        _StubProvider("local", _good_fields()), azure
    )

    provider.detect(_document())

    assert provider.last_diagnostics is None


def test_azure_diagnostics_are_reported_after_an_escalation() -> None:
    azure = _StubProvider("azure", _good_fields(30))
    marker = object()
    azure.last_diagnostics = marker  # type: ignore[attr-defined]
    provider = HybridFieldDetectionProvider(
        _StubProvider("local", _poor_fields()), azure
    )

    provider.detect(_document())

    assert provider.last_diagnostics is marker


def test_a_failed_escalation_reports_no_diagnostics() -> None:
    azure = _StubProvider("azure", error=RuntimeError("boom"))
    azure.last_diagnostics = object()  # type: ignore[attr-defined]
    provider = HybridFieldDetectionProvider(
        _StubProvider("local", _poor_fields()), azure
    )

    provider.detect(_document())

    assert provider.last_diagnostics is None
