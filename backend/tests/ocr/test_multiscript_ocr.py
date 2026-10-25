"""Tests for multi-script OCR & userLanguage decoupling (Phase S1-03).

Verifies:
- SUPPORTED_OCR_LANGUAGES supports en, de, fr, ar, tr, uk, es, and multi-script auto.
- PrepareQuestionsService._run_ocr invokes OCR with language="auto" rather than
  collapsing OCR script selection onto the applicant's UI user_language.
- LocalOCRProvider("auto") intersects requested multi-script packs against installed
  Tesseract packs so environments with partial packs never crash.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from app.core.config import settings
from app.database.session import SessionLocal
from app.documents.service import SourceDocumentService
from app.field_detection.orchestration import PrepareQuestionsService
from app.ocr.constants import SUPPORTED_OCR_LANGUAGES
from app.ocr.models import OCRResult
from app.ocr.providers.local import LocalOCRProvider


def test_supported_ocr_languages_include_turkish_ukrainian_spanish_and_auto() -> None:
    assert SUPPORTED_OCR_LANGUAGES["tr"] == "tur"
    assert SUPPORTED_OCR_LANGUAGES["uk"] == "ukr"
    assert SUPPORTED_OCR_LANGUAGES["es"] == "spa"
    assert "auto" in SUPPORTED_OCR_LANGUAGES
    for pack in ("deu", "eng", "fra", "ara", "tur", "ukr", "spa"):
        assert pack in SUPPORTED_OCR_LANGUAGES["auto"]


@pytest.mark.asyncio
async def test_prepare_questions_runs_multiscript_auto_ocr_independent_of_user_language(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "STORAGE_PROVIDER", "local")
    monkeypatch.setattr(settings, "DOCUMENT_STORAGE_PATH", str(tmp_path / "storage"))
    monkeypatch.setattr(settings, "OCR_PROVIDER", "mock")

    # Upload a smartphone camera photo (normalized to scanned_pdf -> ocr_required)
    img = Image.new("RGB", (600, 800), color=(255, 255, 255))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")

    db = SessionLocal()
    try:
        doc_service = SourceDocumentService(db)
        doc, token = doc_service.upload_and_analyze(
            filename="auslaenderbehoerde_scan.jpg",
            content_type="image/jpeg",
            file_chunks=[buf.getvalue()],
            privacy_accepted=True,
            user_language="ar",
            output_language="ar",
        )
        assert (doc.analysis_result or {}).get("next_step") == "ocr_required"

        # User speaks Arabic ("ar") — OCR MUST still run with "auto", NOT "ar"!
        orchestrator = PrepareQuestionsService(db)
        result = await orchestrator.prepare(doc.public_id, token, user_language="ar")
        assert result.status in ("ready", "needs_clarification")

        ocr_row = (
            db.query(OCRResult).filter(OCRResult.source_document_id == doc.id).one()
        )
        assert ocr_row.language == "auto"
    finally:
        db.close()


def test_local_ocr_provider_auto_intersects_installed_tesseract_packs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import pytesseract

    captured_langs: list[str] = []

    monkeypatch.setattr(pytesseract, "get_tesseract_version", lambda: "5.3.0")
    monkeypatch.setattr(
        pytesseract,
        "get_languages",
        lambda config="": ["eng", "deu", "ara", "tur", "osd"],
    )

    def _fake_image_to_data(
        image: Any, lang: str = "eng", output_type: Any = None
    ) -> dict[str, list[Any]]:
        captured_langs.append(lang)
        return {
            "text": ["Familienname"],
            "conf": ["94.0"],
            "block_num": [1],
            "par_num": [1],
            "line_num": [1],
            "left": [20],
            "top": [40],
            "width": [120],
            "height": [24],
        }

    monkeypatch.setattr(pytesseract, "image_to_data", _fake_image_to_data)

    img_path = tmp_path / "page_1.png"
    Image.new("RGB", (300, 200), color="white").save(img_path, format="PNG")

    provider = LocalOCRProvider()
    page_res = provider.extract_page(img_path, page_number=1, language="auto")
    assert page_res.text == "Familienname"
    assert len(captured_langs) == 1
    assert captured_langs[0] == "deu+eng+ara+tur"
