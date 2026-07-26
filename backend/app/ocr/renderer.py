"""Renders PDF pages to private temporary images for OCR providers to consume.

Coordinates produced by OCR providers are defined in the pixel space of the
image this module writes (see ADR 0009), so DPI must stay consistent between
rendering and downstream normalization.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import fitz

from app.ocr.errors import OCRProviderUnavailableError


@dataclass(frozen=True)
class RenderedPage:
    page_number: int
    image_path: Path
    width: int
    height: int


class PageRenderer(Protocol):
    def render_pages(self, pdf_path: Path, output_dir: Path) -> list[RenderedPage]: ...

    def cleanup(self, pages: list[RenderedPage]) -> None: ...


class PDFPageRenderer:
    """Rotation-aware PDF-to-image renderer backed by PyMuPDF.

    Applies each page's own /Rotate value (via PyMuPDF's rendering matrix) so
    OCR always sees pages in reading orientation.
    """

    def __init__(self, dpi: int = 300):
        self.dpi = dpi

    def render_pages(self, pdf_path: Path, output_dir: Path) -> list[RenderedPage]:
        output_dir.mkdir(parents=True, exist_ok=True)
        rendered: list[RenderedPage] = []
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            raise OCRProviderUnavailableError(
                "Unable to open document for rendering."
            ) from e

        try:
            zoom = self.dpi / 72.0
            matrix = fitz.Matrix(zoom, zoom)
            for index in range(doc.page_count):
                page = doc.load_page(index)
                pixmap = page.get_pixmap(matrix=matrix)
                image_path = output_dir / f"{uuid.uuid4()}.png"
                pixmap.save(str(image_path))
                rendered.append(
                    RenderedPage(
                        page_number=index + 1,
                        image_path=image_path,
                        width=pixmap.width,
                        height=pixmap.height,
                    )
                )
        except Exception as e:
            self.cleanup(rendered)
            raise OCRProviderUnavailableError("Unable to render document pages.") from e
        finally:
            doc.close()

        return rendered

    def cleanup(self, pages: list[RenderedPage]) -> None:
        for rendered_page in pages:
            try:
                rendered_page.image_path.unlink(missing_ok=True)
            except OSError:
                pass
