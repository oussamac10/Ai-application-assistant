"""Automatic document-language detection.

The bug being guarded: the pipeline assumed every document was English, so a
German contract was stored as `en` and — because the assumption matched an
English interface — was never translated at all. Getting `de` and `ar` right,
and refusing to guess when there is nothing to go on, is the whole contract.
"""

from __future__ import annotations

import pytest

from app.language.detector import (
    UNDETERMINED,
    LocalDocumentLanguageDetector,
    MockDocumentLanguageDetector,
)

GERMAN = (
    "Mietvertrag für Wohnraum. Der Vermieter und der Mieter schließen den "
    "folgenden Vertrag. Die Miete beträgt monatlich Euro und ist im Voraus zu "
    "zahlen. Das Mietverhältnis beginnt am ersten Tag des Monats."
)
ENGLISH = (
    "Rental agreement for residential premises. The landlord and the tenant "
    "agree as follows. The rent is payable monthly in advance and the tenancy "
    "begins on the first day of the month."
)
FRENCH = (
    "Contrat de location pour un logement. Le bailleur et le locataire "
    "conviennent de ce qui suit. Le loyer est payable mensuellement et le bail "
    "commence le premier jour du mois."
)
ARABIC = (
    "عقد إيجار سكني. يتفق المؤجر والمستأجر على ما يلي. تدفع الأجرة شهريا في "
    "بداية كل شهر. الاسم الكامل ومكان الميلاد والرمز البريدي."
)


@pytest.fixture
def detector() -> LocalDocumentLanguageDetector:
    return LocalDocumentLanguageDetector()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "text,expected",
    [(GERMAN, "de"), (ENGLISH, "en"), (FRENCH, "fr"), (ARABIC, "ar")],
)
async def test_detects_the_document_language(
    detector: LocalDocumentLanguageDetector, text: str, expected: str
) -> None:
    result = await detector.detect(text)
    assert result.language == expected
    assert 0.0 < result.confidence <= 1.0
    assert result.provider == "local"


@pytest.mark.asyncio
async def test_arabic_is_marked_right_to_left(
    detector: LocalDocumentLanguageDetector,
) -> None:
    """Field-detection geometry keys off this: an RTL document associates a
    blank with the label on its right."""
    assert (await detector.detect(ARABIC)).is_rtl is True
    assert (await detector.detect(GERMAN)).is_rtl is False


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["", "   ", "Name", "Name Date Ort", "12345 67890"])
async def test_insufficient_text_returns_und_rather_than_guessing(
    detector: LocalDocumentLanguageDetector, text: str
) -> None:
    """Guessing "en" here is exactly what caused the original bug."""
    result = await detector.detect(text)
    assert result.language == UNDETERMINED
    assert result.is_determined is False


@pytest.mark.asyncio
async def test_german_form_labels_without_prose_are_still_german(
    detector: LocalDocumentLanguageDetector,
) -> None:
    """Real forms are mostly labels, not sentences."""
    labels = (
        "Vermieter Name Straße Nr PLZ Ort Mieter Name Kaution Miete "
        "Nebenkosten Konto Unterschrift Datum Wohnfläche Größe"
    )
    assert (await detector.detect(labels)).language == "de"


@pytest.mark.asyncio
async def test_arabic_script_wins_over_latin_noise(
    detector: LocalDocumentLanguageDetector,
) -> None:
    """A form mixing Arabic labels with Latin identifiers (IBAN, BIC, email)
    is Arabic — script is decisive, not word statistics."""
    mixed = ARABIC + " IBAN BIC SWIFT email www info form 2026 DE89 3704"
    assert (await detector.detect(mixed)).language == "ar"


@pytest.mark.asyncio
async def test_detection_is_deterministic(
    detector: LocalDocumentLanguageDetector,
) -> None:
    first = await detector.detect(GERMAN)
    second = await detector.detect(GERMAN)
    assert (first.language, first.confidence) == (second.language, second.confidence)


@pytest.mark.asyncio
async def test_mock_detector_returns_what_it_was_told() -> None:
    mock = MockDocumentLanguageDetector("ar", 0.9)
    result = await mock.detect("anything at all")
    assert (result.language, result.confidence, mock.calls) == ("ar", 0.9, 1)


@pytest.mark.asyncio
async def test_document_text_is_never_logged(
    detector: LocalDocumentLanguageDetector, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level("DEBUG"):
        await detector.detect("Name")
        await detector.detect(GERMAN)
    assert "Mietvertrag" not in caplog.text
    assert "Vermieter" not in caplog.text
