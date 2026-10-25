"""Tests for embedded NotoSans / NotoSansArabic PDF overlay & watermarked preview (S1-04).

Verifies:
- Dynamic coordinate-overlay PDF exports embed Unicode Type0 NotoSans / NotoSansArabic
  fonts and render Arabic (RTL shaped, right-aligned), Ukrainian Cyrillic, and Turkish
  diacritics cleanly with real rendered ink inside each target field box.
- `GET /api/form-sessions/{session_id}/preview-pdf` enforces session ownership (401 on
  missing/invalid credentials), renders in-progress answers with a diagonal watermark
  across every page, and leaves `form_exports` untouched.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient

from app.answers.models import FormAnswer
from app.core.config import settings
from app.database.session import SessionLocal
from app.documents.service import SourceDocumentService
from app.field_detection.models import DetectedField, FieldDetectionResult
from app.forms.models import FormField, FormTemplate, FormVersion
from app.main import app
from app.pdf.models import FormExport
from app.pdf.services import PDFExportService
from app.sessions.services import SessionService
from app.storage.factory import get_storage_provider


def _create_blank_form_pdf() -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 90), "Multilingual Form Overlay Test", fontsize=13)
    # Draw light borders around the 3 answer boxes
    for y in (130, 190, 250):
        page.draw_rect(
            fitz.Rect(160, y, 520, y + 26), color=(0.75, 0.75, 0.75), width=0.5
        )
    raw = doc.tobytes()
    doc.close()
    return raw


def _setup_multilingual_dynamic_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    session_status: str = "ready_for_export",
) -> tuple[str, str, str]:
    monkeypatch.setattr(settings, "STORAGE_PROVIDER", "local")
    monkeypatch.setattr(settings, "DOCUMENT_STORAGE_PATH", str(tmp_path / "docs"))
    monkeypatch.setattr(settings, "PDF_EXPORT_DIRECTORY", str(tmp_path / "exports"))

    db = SessionLocal()
    try:
        doc_service = SourceDocumentService(db)
        doc, _doc_tok = doc_service.upload_and_analyze(
            filename="multilingual_form.pdf",
            content_type="application/pdf",
            file_chunks=[_create_blank_form_pdf()],
            privacy_accepted=True,
            user_language="ar",
            output_language="ar",
        )

        det = FieldDetectionResult(
            source_document_id=doc.id,
            status="completed",
            provider_name="local",
            analysis_version=1,
            source_type="digital_pdf",
            field_count=3,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        db.add(det)
        db.flush()

        specs = [
            (
                "arabic_name",
                "الاسم الكامل",
                {"x": 160.0, "y": 130.0, "width": 360.0, "height": 26.0},
                "محمد بن عبد الله",
            ),
            (
                "ukrainian_name",
                "Ім'я та прізвище",
                {"x": 160.0, "y": 190.0, "width": 360.0, "height": 26.0},
                "Олександр Коваленко",
            ),
            (
                "turkish_city",
                "Adres",
                {"x": 160.0, "y": 250.0, "width": 360.0, "height": 26.0},
                "Çağrı Şahin — İstanbul Şişli",
            ),
        ]

        tmpl = FormTemplate(key=f"dyn-unicode-{doc.public_id[:8]}", name="Unicode Form")
        db.add(tmpl)
        db.flush()
        ver = FormVersion(
            form_template_id=tmpl.id,
            version_number=1,
            status="published",
            origin="dynamic_detection",
            source_language="de",
            supported_output_languages=["de", "ar", "uk", "tr", "en"],
        )
        db.add(ver)
        db.flush()

        form_fields: list[tuple[FormField, str]] = []
        for idx, (key, label, bbox, val) in enumerate(specs, start=1):
            df = DetectedField(
                detection_result_id=det.id,
                page_number=1,
                display_order=idx,
                label=label,
                normalized_name=key,
                field_type="text",
                required=True,
                confidence=0.95,
                source="native",
                review_status="confirmed",
                input_bounding_box=bbox,
            )
            db.add(df)
            ff = FormField(
                form_version_id=ver.id,
                key=key,
                field_type="text",
                position=idx,
                required=True,
                requiredness="required",
            )
            db.add(ff)
            form_fields.append((ff, val))
        db.commit()

        sess_service = SessionService(db)
        session, sess_token = sess_service.create_session(
            form_version_id=ver.id,
            user_language="ar",
            output_language="de",
            source_document_id=doc.id,
        )

        for ff, val in form_fields:
            db.add(
                FormAnswer(
                    session_id=session.id,
                    field_id=ff.id,
                    original_language="ar",
                    original_answer=val,
                    normalized_value={"value": val},
                    output_value=val,
                    status="confirmed",
                    validation_status="valid",
                    translation_status="not_required",
                    confirmed_by_user=True,
                )
            )
        session.status = session_status
        db.commit()
        return session.id, session.public_id, sess_token
    finally:
        db.close()


def _count_dark_ink_pixels(page: fitz.Page, clip: fitz.Rect) -> int:
    pix = page.get_pixmap(clip=clip, dpi=150, alpha=False)
    samples = pix.samples
    dark = 0
    for idx in range(0, len(samples), 3):
        if samples[idx] < 120 and samples[idx + 1] < 120 and samples[idx + 2] < 140:
            dark += 1
    return dark


def test_dynamic_overlay_embeds_noto_fonts_for_arabic_cyrillic_and_turkish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _internal_id, session_public_id, sess_token = _setup_multilingual_dynamic_session(
        tmp_path, monkeypatch, session_status="ready_for_export"
    )

    db = SessionLocal()
    try:
        export = PDFExportService(db).create_export(session_public_id, sess_token)
        pdf_bytes = get_storage_provider().get_bytes(export.storage_path)
    finally:
        db.close()

    pdf = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        page = pdf[0]
        fonts = page.get_fonts()
        font_names = " ".join(str(f[3]) for f in fonts)
        encodings = {str(f[5]) for f in fonts}

        # Embedded Type0 Identity-H Noto fonts must be present (not Base-14 Helvetica only)
        assert "Identity-H" in encodings, f"Expected Identity-H Unicode font in {fonts}"
        assert "Noto" in font_names, f"Expected Noto font family in {fonts}"

        extracted = page.get_text()
        assert "Олександр Коваленко" in extracted
        assert "Çağrı Şahin — İstanbul Şişli" in extracted

        # Visual verification at 150 DPI: all 3 boxes must contain rendered dark ink,
        # and Arabic RTL text must be right-aligned (more ink on right half than far-left quarter).
        arabic_box_inner = fitz.Rect(164, 133, 516, 153)
        cyrillic_box_inner = fitz.Rect(164, 193, 516, 213)
        turkish_box_inner = fitz.Rect(164, 253, 516, 273)

        assert _count_dark_ink_pixels(page, arabic_box_inner) > 40
        assert _count_dark_ink_pixels(page, cyrillic_box_inner) > 40
        assert _count_dark_ink_pixels(page, turkish_box_inner) > 40

        arabic_right_half = fitz.Rect(340, 133, 516, 153)
        arabic_far_left = fitz.Rect(164, 133, 240, 153)
        assert _count_dark_ink_pixels(page, arabic_right_half) > _count_dark_ink_pixels(
            page, arabic_far_left
        )
    finally:
        pdf.close()


def test_watermarked_preview_pdf_works_in_progress_enforces_ownership_and_creates_no_export_row(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    internal_session_id, session_public_id, sess_token = (
        _setup_multilingual_dynamic_session(
            tmp_path, monkeypatch, session_status="in_progress"
        )
    )
    client = TestClient(app)

    # 1. Missing or invalid session credentials -> 401
    unauth = client.get(f"/api/form-sessions/{session_public_id}/preview-pdf")
    assert unauth.status_code == 401
    wrong = client.get(
        f"/api/form-sessions/{session_public_id}/preview-pdf",
        headers={"X-Session-Token": "invalid-token"},
    )
    assert wrong.status_code == 401

    # 2. Valid session owner gets watermarked PDF even while session is still in_progress
    resp = client.get(
        f"/api/form-sessions/{session_public_id}/preview-pdf",
        headers={"X-Session-Token": sess_token},
    )
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("application/pdf")
    assert resp.content.startswith(b"%PDF")

    preview_pdf = fitz.open(stream=resp.content, filetype="pdf")
    try:
        text = preview_pdf[0].get_text()
        assert "PREVIEW" in text
        assert "NOT FOR OFFICIAL SUBMISSION" in text
        assert "Олександр Коваленко" in text
    finally:
        preview_pdf.close()

    # 3. Preview must NOT create or mutate persistent FormExport rows
    db = SessionLocal()
    try:
        exports = (
            db.query(FormExport)
            .filter(FormExport.session_id == internal_session_id)
            .all()
        )
        assert exports == []
    finally:
        db.close()
