"""MockOCRProvider — deterministic OCR provider for automated tests and local dev.

No external OCR binary is invoked. Output is fully derived from the page
number and language, so identical inputs always produce identical results.
"""

from __future__ import annotations

from pathlib import Path

from app.ocr.errors import OCRProviderUnavailableError
from app.ocr.providers.base import BoundingBox, OCRLine, OCRPageResult, OCRWord

_PAGE_WIDTH = 2480
_PAGE_HEIGHT = 3508
_BASE_CONFIDENCE = 95.0


class MockOCRProvider:
    """Deterministic OCR provider.

    Args:
        simulate_failure: if True, every extract_page call raises
            OCRProviderUnavailableError, simulating a provider outage.
        simulate_empty: if True, every extract_page call returns a page
            result with no text/lines, simulating a blank or unreadable scan.
    """

    provider_name = "mock"
    provider_version = "1"

    def __init__(
        self,
        simulate_failure: bool = False,
        simulate_empty: bool = False,
    ) -> None:
        self.simulate_failure = simulate_failure
        self.simulate_empty = simulate_empty

    def extract_page(
        self,
        image_path: Path,
        page_number: int,
        language: str | None = None,
    ) -> OCRPageResult:
        if self.simulate_failure:
            raise OCRProviderUnavailableError(
                f"MockOCRProvider simulated failure for page {page_number}."
            )

        if self.simulate_empty:
            return OCRPageResult(
                page_number=page_number,
                width=_PAGE_WIDTH,
                height=_PAGE_HEIGHT,
                text="",
                average_confidence=0.0,
                lines=(),
            )

        lang = language or "en"
        line_text = f"Mock OCR page {page_number} ({lang})"
        words: list[OCRWord] = []
        x_cursor = 100
        y_position = 200
        word_confidence = _BASE_CONFIDENCE
        for token in line_text.split(" "):
            word_width = max(len(token) * 20, 10)
            words.append(
                OCRWord(
                    text=token,
                    confidence=word_confidence,
                    bounding_box=BoundingBox(
                        x=x_cursor, y=y_position, width=word_width, height=40
                    ),
                )
            )
            x_cursor += word_width + 15

        line = OCRLine(
            text=line_text,
            confidence=word_confidence,
            bounding_box=BoundingBox(
                x=100, y=y_position, width=x_cursor - 115, height=40
            ),
            words=tuple(words),
        )

        return OCRPageResult(
            page_number=page_number,
            width=_PAGE_WIDTH,
            height=_PAGE_HEIGHT,
            text=line_text,
            average_confidence=word_confidence,
            lines=(line,),
        )
