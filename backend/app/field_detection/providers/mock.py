"""MockFieldDetectionProvider — deterministic detection provider for tests
and local dev.

No AI or external dependency is invoked. Default output is fully derived
from the input document's page geometry, so identical inputs always
produce identical candidates.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.field_detection.errors import FieldDetectionProviderUnavailableError
from app.field_detection.providers.base import (
    BoundingBox,
    DetectedFieldCandidate,
    DetectionDocumentInput,
    DetectionResult,
)

_DEFAULT_CONFIDENCE = 0.93
_LOW_CONFIDENCE = 0.2


class MockFieldDetectionProvider:
    """Deterministic detection provider.

    Args:
        candidates: if provided, `detect` always returns exactly these
            candidates, ignoring the input document (fully configurable
            output for tests that need specific scenarios).
        simulate_failure: if True, every `detect` call raises
            FieldDetectionProviderUnavailableError, simulating an outage.
        simulate_empty: if True, every `detect` call returns a result with
            no candidate fields, simulating a document with no detectable
            evidence.
        simulate_low_confidence: if True, the one default candidate per page
            is produced with a low confidence and field_type "unknown"
            instead of the default deterministic guess.
    """

    provider_name = "mock"
    provider_version = "1"

    def __init__(
        self,
        candidates: Sequence[DetectedFieldCandidate] | None = None,
        simulate_failure: bool = False,
        simulate_empty: bool = False,
        simulate_low_confidence: bool = False,
    ) -> None:
        self.candidates = list(candidates) if candidates is not None else None
        self.simulate_failure = simulate_failure
        self.simulate_empty = simulate_empty
        self.simulate_low_confidence = simulate_low_confidence

    def detect(self, document: DetectionDocumentInput) -> DetectionResult:
        if self.simulate_failure:
            raise FieldDetectionProviderUnavailableError(
                "MockFieldDetectionProvider simulated failure."
            )

        if self.simulate_empty:
            return DetectionResult(
                provider_name=self.provider_name,
                provider_version=self.provider_version,
                fields=(),
            )

        if self.candidates is not None:
            return DetectionResult(
                provider_name=self.provider_name,
                provider_version=self.provider_version,
                fields=tuple(self.candidates),
            )

        fields: list[DetectedFieldCandidate] = []
        for page in document.pages:
            fields.append(self._default_candidate_for_page(page.page_number))

        return DetectionResult(
            provider_name=self.provider_name,
            provider_version=self.provider_version,
            fields=tuple(fields),
        )

    def _default_candidate_for_page(self, page_number: int) -> DetectedFieldCandidate:
        y_position = 100 + (page_number - 1) * 20

        if self.simulate_low_confidence:
            return DetectedFieldCandidate(
                candidate_key=f"page{page_number}-candidate1",
                page_number=page_number,
                label=f"Mock field page {page_number}",
                normalized_name=f"mock_field_page_{page_number}",
                field_type="unknown",
                confidence=_LOW_CONFIDENCE,
                source="native",
                label_bounding_box=BoundingBox(
                    x=100, y=y_position, width=150, height=20
                ),
                input_bounding_box=BoundingBox(
                    x=260, y=y_position, width=200, height=20
                ),
            )

        return DetectedFieldCandidate(
            candidate_key=f"page{page_number}-candidate1",
            page_number=page_number,
            label=f"Mock field page {page_number}",
            normalized_name=f"mock_field_page_{page_number}",
            field_type="text",
            confidence=_DEFAULT_CONFIDENCE,
            source="native",
            label_bounding_box=BoundingBox(x=100, y=y_position, width=150, height=20),
            input_bounding_box=BoundingBox(x=260, y=y_position, width=200, height=20),
        )
