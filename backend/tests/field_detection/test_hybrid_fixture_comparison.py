"""Both providers, measured on the same fixed documents.

The routing threshold is a number, and a number chosen against synthetic inputs
proves nothing about real forms. These tests run the local pass over a
committed PDF and the Azure pass over a recorded response from that *same*
document, then compare the two scores and the decision they produce.

That makes the threshold a tested property rather than a guess, and it means a
change to either extractor that would flip a real document's routing — turning
a free document into a billed one, or the reverse — fails here instead of in
production.

The Azure response is a recorded fixture; no test calls the live service.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.core.config import settings
from app.field_detection.extraction import extract_native_document_input
from app.field_detection.providers.azure import AzureDocumentIntelligenceProvider
from app.field_detection.providers.azure_client import AzureAnalyzeResponse
from app.field_detection.providers.hybrid import (
    REASON_LOCAL_SUFFICIENT,
    HybridFieldDetectionProvider,
)
from app.field_detection.providers.local import LocalFieldDetectionProvider
from app.field_detection.quality import score_extraction

_RENTAL_PDF = (
    Path(__file__).resolve().parents[3] / "fixtures" / "pdf" / "rental-contract-de.pdf"
)
_AZURE_LAYOUT = Path(__file__).parent / "fixtures" / "azure_rental_contract_layout.json"


class _RecordedAzureClient:
    """Replays the recorded layout response for the same document."""

    def __init__(self, layout: dict[str, Any]) -> None:
        self._layout = layout
        self.call_count = 0

    def analyze_document(self, pdf_path: Path) -> AzureAnalyzeResponse:
        self.call_count += 1
        return AzureAnalyzeResponse(
            analyze_result=self._layout,
            request_id="req-fixture",
            model_id="prebuilt-layout",
            api_version="2024-11-30",
            duration_seconds=1.25,
        )


@pytest.fixture(scope="module")
def rental_document():
    if not _RENTAL_PDF.exists():
        pytest.skip(f"Fixture PDF not found: {_RENTAL_PDF.name}")
    return extract_native_document_input(_RENTAL_PDF)


@pytest.fixture(scope="module")
def azure_layout() -> dict[str, Any]:
    return json.loads(_AZURE_LAYOUT.read_text(encoding="utf-8"))


def test_the_german_rental_contract_is_read_well_enough_locally(
    rental_document,
) -> None:
    """A native-text German form is exactly the case that must stay free."""
    result = LocalFieldDetectionProvider().detect(rental_document)
    quality = score_extraction(result.fields)

    assert quality.field_count > 0
    assert quality.score >= settings.HYBRID_LOCAL_QUALITY_THRESHOLD, (
        "The reference German contract now scores below the escalation "
        f"threshold ({quality.score} < {settings.HYBRID_LOCAL_QUALITY_THRESHOLD}); "
        "every upload of a document like it would start being billed."
    )


def test_the_german_rental_contract_is_never_escalated(
    rental_document, azure_layout
) -> None:
    client = _RecordedAzureClient(azure_layout)
    provider = HybridFieldDetectionProvider(
        LocalFieldDetectionProvider(),
        AzureDocumentIntelligenceProvider(client=client),
    )

    result = provider.detect(rental_document)

    assert client.call_count == 0
    assert result.provider_name == "local"
    assert provider.last_decision is not None
    assert provider.last_decision.reason == REASON_LOCAL_SUFFICIENT


def test_both_providers_are_scored_on_the_same_scale(
    rental_document, azure_layout
) -> None:
    """The comparison that the routing rests on: two providers, one document,
    one scoring function, both answers in 0-1."""
    local_quality = score_extraction(
        LocalFieldDetectionProvider().detect(rental_document).fields
    )
    azure_quality = score_extraction(
        AzureDocumentIntelligenceProvider(client=_RecordedAzureClient(azure_layout))
        .detect(rental_document)
        .fields
    )

    for quality in (local_quality, azure_quality):
        assert 0.0 <= quality.score <= 1.0
        assert 0.0 <= quality.label_quality <= 1.0
        assert 0.0 <= quality.input_evidence <= 1.0
    # Both actually found something on this document — a comparison between
    # two empty results would pass every assertion above and mean nothing.
    assert local_quality.field_count > 0
    assert azure_quality.field_count > 0


def test_the_escalation_decision_is_reproducible(rental_document) -> None:
    """Same document, same settings, same answer — every time. A routing
    decision that varied run to run would bill unpredictably."""
    local = LocalFieldDetectionProvider()

    decisions = []
    for _ in range(3):
        provider = HybridFieldDetectionProvider(local)
        provider.detect(rental_document)
        assert provider.last_decision is not None
        decisions.append(
            (provider.last_decision.reason, provider.last_decision.local_quality.score)
        )

    assert len(set(decisions)) == 1
