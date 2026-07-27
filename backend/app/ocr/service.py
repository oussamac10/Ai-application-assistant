from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.documents.models import SourceDocument
from app.documents.service import SourceDocumentService
from app.ocr.constants import SUPPORTED_OCR_LANGUAGES
from app.ocr.errors import (
    OCRAlreadyProcessingError,
    OCRNotFoundError,
    OCRValidationError,
)
from app.ocr.models import OCRPage, OCRResult
from app.ocr.providers.base import OCRLine, OCRProvider
from app.ocr.providers.mock import MockOCRProvider
from app.ocr.renderer import PageRenderer, RenderedPage
from app.ocr.repository import OCRRepository


def build_default_provider() -> OCRProvider:
    if settings.OCR_PROVIDER == "mock":
        return MockOCRProvider()
    if settings.OCR_PROVIDER == "local":
        from app.ocr.providers.local import LocalOCRProvider

        return LocalOCRProvider()
    raise OCRValidationError(
        f"Unknown OCR provider '{settings.OCR_PROVIDER}'.", "ocr_misconfigured"
    )


def build_default_renderer() -> PageRenderer:
    from app.ocr.renderer import PDFPageRenderer

    return PDFPageRenderer(dpi=settings.OCR_RENDER_DPI)


class OCRService:
    def __init__(
        self,
        db: Session,
        provider: OCRProvider | None = None,
        renderer: PageRenderer | None = None,
        current_user_id: str | None = None,
    ):
        self.db = db
        self.repo = OCRRepository()
        self.document_service = SourceDocumentService(db)
        self._provider = provider
        self._renderer = renderer
        # See FieldDetectionService for the same dual-ownership rationale.
        self.current_user_id = current_user_id

    @property
    def provider(self) -> OCRProvider:
        if self._provider is None:
            self._provider = build_default_provider()
        return self._provider

    @property
    def renderer(self) -> PageRenderer:
        if self._renderer is None:
            self._renderer = build_default_renderer()
        return self._renderer

    def _check_eligibility(self, doc: SourceDocument, language: str) -> None:
        if language not in SUPPORTED_OCR_LANGUAGES:
            raise OCRValidationError(
                f"Unsupported OCR language '{language}'.", "unsupported_language"
            )

        analysis = doc.analysis_result or {}
        next_step = analysis.get("next_step")
        if next_step != "ocr_required" and not doc.is_probably_scanned:
            raise OCRValidationError(
                "This document does not require OCR.", "ocr_not_required"
            )

    def request_ocr(
        self, document_public_id: str, ownership_token: str | None, language: str
    ) -> OCRResult:
        doc = self.document_service.get_document(
            document_public_id, ownership_token, self.current_user_id
        )
        self._check_eligibility(doc, language)

        existing = self.repo.get_by_source_document_id(self.db, doc.id)
        if existing is not None:
            if existing.status == "processing":
                raise OCRAlreadyProcessingError(
                    "OCR is already in progress for this document."
                )
            if existing.status == "completed":
                return existing

        now = datetime.now(UTC)
        expires_at = now + timedelta(hours=settings.OCR_EXPIRATION_HOURS)

        if existing is None:
            result = OCRResult(
                source_document_id=doc.id,
                status="processing",
                language=language,
                expires_at=expires_at,
                created_at=now,
                updated_at=now,
            )
            result = self.repo.create(self.db, result)
        else:
            result = existing
            result.status = "processing"
            result.language = language
            result.error_code = None
            result.error_message = None
            result.expires_at = expires_at
            result = self.repo.update(self.db, result)

        rendered_pages: list[RenderedPage] = []
        try:
            output_dir = self._render_output_dir(result.id)
            rendered_pages = self.renderer.render_pages(
                pdf_path=Path(doc.storage_path), output_dir=output_dir
            )

            pages: list[OCRPage] = []
            for rendered in rendered_pages:
                page_result = self.provider.extract_page(
                    rendered.image_path, rendered.page_number, language
                )
                pages.append(
                    OCRPage(
                        page_number=page_result.page_number,
                        width=page_result.width,
                        height=page_result.height,
                        text=page_result.text,
                        average_confidence=page_result.average_confidence,
                        lines=[_line_to_dict(line) for line in page_result.lines],
                    )
                )

            result.status = "completed"
            result.provider_name = self.provider.provider_name
            result.provider_version = self.provider.provider_version
            result.page_count = len(pages)
            self.repo.replace_pages(self.db, result, pages)
        except OCRValidationError:
            raise
        except Exception as e:
            result.status = "failed"
            result.error_code = "ocr_failed"
            result.error_message = "OCR processing failed."
            self.repo.update(self.db, result)
            raise OCRValidationError("OCR processing failed.", "ocr_failed") from e
        finally:
            self.renderer.cleanup(rendered_pages)
            try:
                output_dir.rmdir()
            except OSError:
                pass

        return result

    def get_ocr_result(
        self, document_public_id: str, ownership_token: str | None
    ) -> OCRResult:
        doc = self.document_service.get_document(
            document_public_id, ownership_token, self.current_user_id
        )
        result = self.repo.get_by_source_document_id(self.db, doc.id)
        if result is None:
            raise OCRNotFoundError("No OCR result exists for this document yet.")
        return result

    def _render_output_dir(self, ocr_result_id: str) -> Path:
        return Path(settings.OCR_RENDER_STORAGE_PATH) / ocr_result_id


def _line_to_dict(line: OCRLine) -> dict[str, Any]:
    return {
        "text": line.text,
        "confidence": line.confidence,
        "boundingBox": {
            "x": line.bounding_box.x,
            "y": line.bounding_box.y,
            "width": line.bounding_box.width,
            "height": line.bounding_box.height,
        },
        "words": [
            {
                "text": word.text,
                "confidence": word.confidence,
                "boundingBox": {
                    "x": word.bounding_box.x,
                    "y": word.bounding_box.y,
                    "width": word.bounding_box.width,
                    "height": word.bounding_box.height,
                },
            }
            for word in line.words
        ],
    }
