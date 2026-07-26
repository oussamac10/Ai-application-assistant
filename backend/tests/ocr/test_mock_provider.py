from pathlib import Path

import pytest

from app.ocr.errors import OCRProviderUnavailableError
from app.ocr.providers.base import OCRProvider
from app.ocr.providers.mock import MockOCRProvider


def test_mock_provider_satisfies_protocol() -> None:
    provider = MockOCRProvider()
    assert isinstance(provider, OCRProvider)
    assert provider.provider_name == "mock"
    assert provider.provider_version


def test_mock_provider_is_deterministic() -> None:
    provider = MockOCRProvider()
    result_a = provider.extract_page(
        Path("/tmp/page-1.png"), page_number=1, language="en"
    )
    result_b = provider.extract_page(
        Path("/tmp/page-1.png"), page_number=1, language="en"
    )

    assert result_a == result_b


def test_mock_provider_produces_text_lines_and_words() -> None:
    provider = MockOCRProvider()
    result = provider.extract_page(
        Path("/tmp/page-1.png"), page_number=1, language="en"
    )

    assert result.page_number == 1
    assert result.text
    assert len(result.lines) == 1
    line = result.lines[0]
    assert line.text == result.text
    assert len(line.words) > 0
    assert all(word.text for word in line.words)


def test_mock_provider_confidence_is_predictable() -> None:
    provider = MockOCRProvider()
    result = provider.extract_page(Path("/tmp/page-1.png"), page_number=1)

    assert result.average_confidence == 95.0
    assert all(word.confidence == 95.0 for word in result.lines[0].words)


def test_mock_provider_bounding_boxes_are_non_negative_and_ordered() -> None:
    provider = MockOCRProvider()
    result = provider.extract_page(Path("/tmp/page-1.png"), page_number=1)

    line = result.lines[0]
    assert line.bounding_box.x >= 0
    assert line.bounding_box.y >= 0

    previous_x = -1
    for word in line.words:
        assert word.bounding_box.x > previous_x
        previous_x = word.bounding_box.x


def test_mock_provider_different_pages_produce_different_text() -> None:
    provider = MockOCRProvider()
    page_1 = provider.extract_page(
        Path("/tmp/page-1.png"), page_number=1, language="en"
    )
    page_2 = provider.extract_page(
        Path("/tmp/page-2.png"), page_number=2, language="en"
    )

    assert page_1.text != page_2.text


def test_mock_provider_language_affects_output() -> None:
    provider = MockOCRProvider()
    en_result = provider.extract_page(
        Path("/tmp/page-1.png"), page_number=1, language="en"
    )
    ar_result = provider.extract_page(
        Path("/tmp/page-1.png"), page_number=1, language="ar"
    )

    assert en_result.text != ar_result.text


def test_mock_provider_simulated_failure_raises() -> None:
    provider = MockOCRProvider(simulate_failure=True)

    with pytest.raises(OCRProviderUnavailableError):
        provider.extract_page(Path("/tmp/page-1.png"), page_number=1)


def test_mock_provider_simulated_empty_result() -> None:
    provider = MockOCRProvider(simulate_empty=True)
    result = provider.extract_page(Path("/tmp/page-1.png"), page_number=1)

    assert result.text == ""
    assert result.lines == ()
    assert result.average_confidence == 0.0
