import pytest

from app.field_detection.errors import FieldDetectionProviderUnavailableError
from app.field_detection.providers.base import (
    BoundingBox,
    DetectedFieldCandidate,
    DetectionDocumentInput,
    DetectionPageInput,
    FieldDetectionProvider,
)
from app.field_detection.providers.mock import MockFieldDetectionProvider


def _make_document(page_count: int = 1) -> DetectionDocumentInput:
    pages = tuple(
        DetectionPageInput(page_number=n, width=612, height=792)
        for n in range(1, page_count + 1)
    )
    return DetectionDocumentInput(page_count=page_count, pages=pages)


def test_mock_provider_satisfies_protocol() -> None:
    provider = MockFieldDetectionProvider()
    assert isinstance(provider, FieldDetectionProvider)
    assert provider.provider_name == "mock"
    assert provider.provider_version


def test_mock_provider_is_deterministic() -> None:
    provider = MockFieldDetectionProvider()
    document = _make_document(page_count=2)

    result_a = provider.detect(document)
    result_b = provider.detect(document)

    assert result_a == result_b


def test_mock_provider_produces_one_candidate_per_page() -> None:
    provider = MockFieldDetectionProvider()
    document = _make_document(page_count=3)

    result = provider.detect(document)

    assert len(result.fields) == 3
    assert [f.page_number for f in result.fields] == [1, 2, 3]
    assert all(f.field_type == "text" for f in result.fields)
    assert all(f.label for f in result.fields)


def test_mock_provider_confidence_is_predictable() -> None:
    provider = MockFieldDetectionProvider()
    result = provider.detect(_make_document(page_count=1))

    assert result.fields[0].confidence == 0.93


def test_mock_provider_simulated_empty_result() -> None:
    provider = MockFieldDetectionProvider(simulate_empty=True)
    result = provider.detect(_make_document(page_count=2))

    assert result.fields == ()


def test_mock_provider_simulated_failure_raises() -> None:
    provider = MockFieldDetectionProvider(simulate_failure=True)

    with pytest.raises(FieldDetectionProviderUnavailableError):
        provider.detect(_make_document(page_count=1))


def test_mock_provider_simulated_low_confidence_is_unknown_type() -> None:
    provider = MockFieldDetectionProvider(simulate_low_confidence=True)
    result = provider.detect(_make_document(page_count=1))

    field = result.fields[0]
    assert field.field_type == "unknown"
    assert field.confidence < 0.4


def test_mock_provider_configurable_candidates_override_default_output() -> None:
    custom_candidate = DetectedFieldCandidate(
        candidate_key="custom-1",
        page_number=1,
        label="Custom Label",
        normalized_name="custom_label",
        field_type="email",
        confidence=0.75,
        source="ocr",
    )
    provider = MockFieldDetectionProvider(candidates=[custom_candidate])

    result = provider.detect(_make_document(page_count=5))

    assert result.fields == (custom_candidate,)


def test_bounding_box_rejects_negative_dimensions() -> None:
    with pytest.raises(ValueError):
        BoundingBox(x=0, y=0, width=-1, height=10)


def test_detected_field_candidate_rejects_unknown_field_type() -> None:
    with pytest.raises(ValueError):
        DetectedFieldCandidate(
            candidate_key="k",
            page_number=1,
            label="x",
            normalized_name="x",
            field_type="not_a_real_type",
            confidence=0.5,
            source="native",
        )


def test_detected_field_candidate_rejects_out_of_range_confidence() -> None:
    with pytest.raises(ValueError):
        DetectedFieldCandidate(
            candidate_key="k",
            page_number=1,
            label="x",
            normalized_name="x",
            field_type="text",
            confidence=1.5,
            source="native",
        )
