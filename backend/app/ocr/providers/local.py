"""LocalOCRProvider — pytesseract-backed OCR provider.

Runs the tesseract binary locally; no data ever leaves the host. Requires the
`tesseract-ocr` system binary plus the language packs listed in
app.ocr.constants.SUPPORTED_OCR_LANGUAGES to be installed (see Dockerfile).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytesseract
from PIL import Image
from pytesseract import Output

from app.ocr.constants import SUPPORTED_OCR_LANGUAGES
from app.ocr.errors import OCRConfigurationError, OCRProviderUnavailableError
from app.ocr.providers.base import BoundingBox, OCRLine, OCRPageResult, OCRWord

_DEFAULT_LANGUAGE = "en"


class LocalOCRProvider:
    provider_name = "local"
    provider_version = "1"

    def __init__(self) -> None:
        try:
            self.provider_version = str(pytesseract.get_tesseract_version())
        except Exception as e:
            raise OCRProviderUnavailableError(
                "The local tesseract binary is not available."
            ) from e

    def extract_page(
        self,
        image_path: Path,
        page_number: int,
        language: str | None = None,
    ) -> OCRPageResult:
        lang = language or _DEFAULT_LANGUAGE
        tesseract_lang = SUPPORTED_OCR_LANGUAGES.get(lang)
        if tesseract_lang is None:
            raise OCRConfigurationError(f"Unsupported OCR language '{lang}'.")

        try:
            with Image.open(image_path) as image:
                width, height = image.size
                data = pytesseract.image_to_data(
                    image, lang=tesseract_lang, output_type=Output.DICT
                )
        except OCRConfigurationError:
            raise
        except Exception as e:
            raise OCRProviderUnavailableError(
                f"Local OCR failed for page {page_number}."
            ) from e

        lines = _group_words_into_lines(data)
        all_confidences = [word.confidence for line in lines for word in line.words]
        average_confidence = (
            sum(all_confidences) / len(all_confidences) if all_confidences else 0.0
        )
        text = "\n".join(line.text for line in lines)

        return OCRPageResult(
            page_number=page_number,
            width=width,
            height=height,
            text=text,
            average_confidence=average_confidence,
            lines=tuple(lines),
        )


def _group_words_into_lines(data: dict[str, list[Any]]) -> list[OCRLine]:
    grouped: dict[tuple[int, int, int], list[OCRWord]] = {}
    order: list[tuple[int, int, int]] = []

    for i in range(len(data["text"])):
        token = data["text"][i].strip()
        confidence = float(data["conf"][i])
        if not token or confidence < 0:
            continue

        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        word = OCRWord(
            text=token,
            confidence=confidence,
            bounding_box=BoundingBox(
                x=int(data["left"][i]),
                y=int(data["top"][i]),
                width=int(data["width"][i]),
                height=int(data["height"][i]),
            ),
        )
        if key not in grouped:
            grouped[key] = []
            order.append(key)
        grouped[key].append(word)

    lines: list[OCRLine] = []
    for key in order:
        words = grouped[key]
        line_text = " ".join(w.text for w in words)
        min_x = min(w.bounding_box.x for w in words)
        min_y = min(w.bounding_box.y for w in words)
        max_x = max(w.bounding_box.x + w.bounding_box.width for w in words)
        max_y = max(w.bounding_box.y + w.bounding_box.height for w in words)
        line_confidence = sum(w.confidence for w in words) / len(words)
        lines.append(
            OCRLine(
                text=line_text,
                confidence=line_confidence,
                bounding_box=BoundingBox(
                    x=min_x, y=min_y, width=max_x - min_x, height=max_y - min_y
                ),
                words=tuple(words),
            )
        )

    return lines
