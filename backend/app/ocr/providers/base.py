"""OCRProvider protocol and provider-independent normalized result types.

Every OCR engine implementation (mock, local, future cloud) returns these
structures. Coordinates are in rendered-image pixel space (the dimensions of
the page image actually handed to the provider), not PDF point space — see
ADR 0009. These types describe text and geometry only; they must never carry
field-semantic information (label/value pairing, form-field inference).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class BoundingBox:
    x: int
    y: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width < 0 or self.height < 0:
            raise ValueError("Bounding box width and height must be non-negative.")
        if self.x < 0 or self.y < 0:
            raise ValueError("Bounding box x and y must be non-negative.")


@dataclass(frozen=True)
class OCRWord:
    text: str
    confidence: float
    bounding_box: BoundingBox


@dataclass(frozen=True)
class OCRLine:
    text: str
    confidence: float
    bounding_box: BoundingBox
    words: tuple[OCRWord, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class OCRPageResult:
    page_number: int
    width: int
    height: int
    text: str
    average_confidence: float
    lines: tuple[OCRLine, ...] = field(default_factory=tuple)


@runtime_checkable
class OCRProvider(Protocol):
    """Provider-independent interface for all OCR operations.

    Business services must depend only on this Protocol, never a concrete
    provider class.
    """

    provider_name: str
    provider_version: str

    def extract_page(
        self,
        image_path: Path,
        page_number: int,
        language: str | None = None,
    ) -> OCRPageResult: ...
