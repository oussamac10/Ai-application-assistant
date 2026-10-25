"""Tests for Phase 17 dynamic coordinate-overlay PDF export and field location metadata."""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import fitz
import pytest
from sqlalchemy import text

from app.answers.models import FormAnswer
from app.answers.services import AnswerService
from app.database.session import SessionLocal
from app.documents.models import SourceDocument
from app.field_detection.models import DetectedField, FieldDetectionResult
from app.forms.models import FormField, FormTemplate, FormVersion
from app.pdf.services import PDFExportService
from app.sessions.models import FormSession
from app.sessions.security import hash_ownership_token


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.execute(text("TRUNCATE TABLE form_exports CASCADE"))
        db.execute(text("TRUNCATE TABLE source_documents CASCADE"))
        db.commit()
        yield
    except Exception:
        db.rollback()
    finally:
        db.close()


def _create_blank_uploaded_pdf(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "uploaded_antrag.pdf"
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text(fitz.Point(72, 80), "Antrag auf Leistungen", fontsize=14)
    page.insert_text(fitz.Point(72, 140), "Vorname:", fontsize=10)
    page.insert_text(fitz.Point(72, 180), "Stadt:", fontsize=10)
    doc.save(str(pdf_path))
    doc.close()
    return pdf_path


def test_dynamic_session_with_detected_coordinates_exports_overlaid_pdf(
    tmp_path: Path,
) -> None:
    db = SessionLocal()
    try:
        uploaded_pdf = _create_blank_uploaded_pdf(tmp_path)
        token = "dynamic-export-token"
        token_hash = hash_ownership_token(token)
        expires = datetime.now(UTC) + timedelta(hours=2)

        source_doc = SourceDocument(
            ownership_token_hash=token_hash,
            original_filename="uploaded_antrag.pdf",
            sanitized_filename="uploaded_antrag.pdf",
            storage_path=str(uploaded_pdf),
            content_type="application/pdf",
            size_bytes=uploaded_pdf.stat().st_size,
            checksum_sha256="a" * 64,
            status="analyzed",
            page_count=1,
            expires_at=expires,
        )
        db.add(source_doc)
        db.commit()

        detection = FieldDetectionResult(
            source_document_id=source_doc.id,
            status="completed",
            provider_name="local",
            analysis_version=1,
            field_count=3,
            expires_at=expires,
        )
        db.add(detection)
        db.commit()

        df_name = DetectedField(
            detection_result_id=detection.id,
            page_number=1,
            display_order=0,
            label="Vorname",
            normalized_name="first_name",
            field_type="text",
            required=True,
            confidence=0.95,
            source="native_text",
            label_bounding_box={"x": 72.0, "y": 130.0, "width": 80.0, "height": 18.0},
            input_bounding_box={"x": 180.0, "y": 130.0, "width": 220.0, "height": 20.0},
            review_status="confirmed",
        )
        df_city = DetectedField(
            detection_result_id=detection.id,
            page_number=1,
            display_order=1,
            label="Stadt",
            normalized_name="city",
            field_type="text",
            required=True,
            confidence=0.92,
            source="native_text",
            label_bounding_box={"x": 72.0, "y": 170.0, "width": 80.0, "height": 18.0},
            input_bounding_box={"x": 180.0, "y": 170.0, "width": 220.0, "height": 20.0},
            review_status="confirmed",
        )
        df_check = DetectedField(
            detection_result_id=detection.id,
            page_number=1,
            display_order=2,
            label="Erstantrag",
            normalized_name="initial_application",
            field_type="checkbox",
            required=False,
            confidence=0.90,
            source="native_text",
            input_bounding_box={"x": 180.0, "y": 210.0, "width": 14.0, "height": 14.0},
            review_status="confirmed",
        )
        db.add_all([df_name, df_city, df_check])
        db.commit()

        template = FormTemplate(
            key=f"dynamic-doc-{source_doc.public_id}",
            name="Dynamic form — uploaded_antrag.pdf",
        )
        db.add(template)
        db.commit()

        version = FormVersion(
            form_template_id=template.id,
            version_number=1,
            status="published",
            source_language="de",
            supported_output_languages=["de", "en"],
            origin="dynamic_detection",
            pdf_template_key=None,
        )
        db.add(version)
        db.commit()

        f_name = FormField(
            form_version_id=version.id,
            key="first_name",
            field_type="person_name",
            required=True,
            requiredness="required",
            position=0,
        )
        f_city = FormField(
            form_version_id=version.id,
            key="city",
            field_type="string",
            required=True,
            requiredness="required",
            position=1,
        )
        f_check = FormField(
            form_version_id=version.id,
            key="initial_application",
            field_type="boolean",
            required=False,
            requiredness="optional",
            position=2,
        )
        db.add_all([f_name, f_city, f_check])
        db.commit()

        session = FormSession(
            form_version_id=version.id,
            source_document_id=source_doc.id,
            user_language="en",
            source_language="de",
            output_language="de",
            ownership_token_hash=token_hash,
            status="ready_for_export",
            expires_at=expires,
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        assert session.export_supported is True

        db.add_all(
            [
                FormAnswer(
                    session_id=session.id,
                    field_id=f_name.id,
                    original_answer="Youssef Alaoui",
                    original_language="en",
                    normalized_value="Youssef Alaoui",
                    output_value="Youssef Alaoui",
                    status="confirmed",
                    confirmed_by_user=True,
                ),
                FormAnswer(
                    session_id=session.id,
                    field_id=f_city.id,
                    original_answer="Berlin",
                    original_language="en",
                    normalized_value="Berlin",
                    output_value="Berlin",
                    status="confirmed",
                    confirmed_by_user=True,
                ),
                FormAnswer(
                    session_id=session.id,
                    field_id=f_check.id,
                    original_answer="true",
                    original_language="en",
                    normalized_value=True,
                    output_value="Ja",
                    status="confirmed",
                    confirmed_by_user=True,
                ),
            ]
        )
        db.commit()

        pdf_dir = tmp_path / "fixtures" / "pdf"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        service = PDFExportService(db, pdf_dir)

        export = service.create_export(session.public_id, token)
        assert export.status == "completed"
        export_path = Path(export.storage_path)
        assert export_path.is_file()

        # Verify the overlaid values appear inside the generated PDF
        rendered_doc = fitz.open(str(export_path))
        try:
            page_text = rendered_doc[0].get_text("text")
        finally:
            rendered_doc.close()

        assert "Youssef Alaoui" in page_text
        assert "Berlin" in page_text

        # Calling create_export a second time is idempotent
        second_export = service.create_export(session.public_id, token)
        assert second_export.id == export.id
    finally:
        db.close()


@pytest.mark.asyncio
async def test_current_field_includes_document_location_metadata(
    tmp_path: Path,
) -> None:
    db = SessionLocal()
    try:
        uploaded_pdf = _create_blank_uploaded_pdf(tmp_path)
        token = "location-meta-token"
        token_hash = hash_ownership_token(token)
        expires = datetime.now(UTC) + timedelta(hours=2)

        source_doc = SourceDocument(
            ownership_token_hash=token_hash,
            original_filename="wohngeld_2026.pdf",
            sanitized_filename="wohngeld_2026.pdf",
            storage_path=str(uploaded_pdf),
            content_type="application/pdf",
            size_bytes=uploaded_pdf.stat().st_size,
            checksum_sha256="b" * 64,
            status="analyzed",
            page_count=2,
            expires_at=expires,
        )
        db.add(source_doc)
        db.commit()

        detection = FieldDetectionResult(
            source_document_id=source_doc.id,
            status="completed",
            provider_name="local",
            analysis_version=1,
            field_count=1,
            expires_at=expires,
        )
        db.add(detection)
        db.commit()

        df = DetectedField(
            detection_result_id=detection.id,
            page_number=2,
            display_order=0,
            label="Postleitzahl",
            normalized_name="postal_code",
            field_type="text",
            required=True,
            confidence=0.95,
            source="native_text",
            input_bounding_box={"x": 140.0, "y": 260.0, "width": 120.0, "height": 18.0},
            review_status="confirmed",
        )
        db.add(df)
        db.commit()

        template = FormTemplate(
            key=f"dynamic-doc-{source_doc.public_id}",
            name="Dynamic form",
        )
        db.add(template)
        db.commit()

        version = FormVersion(
            form_template_id=template.id,
            version_number=1,
            status="published",
            source_language="de",
            supported_output_languages=["de", "en"],
            origin="dynamic_detection",
            pdf_template_key=None,
        )
        db.add(version)
        db.commit()

        field = FormField(
            form_version_id=version.id,
            key="postal_code",
            field_type="string",
            required=True,
            requiredness="required",
            position=0,
        )
        db.add(field)
        db.commit()

        session = FormSession(
            form_version_id=version.id,
            source_document_id=source_doc.id,
            user_language="en",
            source_language="de",
            output_language="de",
            ownership_token_hash=token_hash,
            status="in_progress",
            expires_at=expires,
        )
        db.add(session)
        db.commit()

        answer_service = AnswerService(db)
        current = await answer_service.get_current_field(session.public_id, token)

        assert current["page_number"] == 2
        assert current["input_bounding_box"] == {
            "x": 140.0,
            "y": 260.0,
            "width": 120.0,
            "height": 18.0,
        }
        assert current["source_document_filename"] == "wohngeld_2026.pdf"
        assert current["source_document_page_count"] == 2
    finally:
        db.close()


@pytest.mark.asyncio
async def test_unmatched_official_acroform_pdf_end_to_end_prepare_and_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end test for an unmatched fillable AcroForm PDF (modeled on the
    Stuttgart Wohnungsgeberbestätigung):
    - Uploads and analyzes as `fillable_pdf` with `next_step == "dynamic_field_detection"`
    - `PrepareQuestionsService.prepare()` creates a guided session with humanized
      numbered person fields (`Person 1`) and party-contextualized labels
      (`Wohnungsgeber – Zuname, Vorname`, `Eigentümer – Zuname, Vorname`)
    - `PDFExportService.create_export()` overlays confirmed answers and draws
      checkmarks inside the selected checkbox widget.
    """
    import fitz

    from app.ai.mock_provider import MockAIProvider
    from app.core.config import settings
    from app.documents.service import SourceDocumentService
    from app.field_detection.orchestration import PrepareQuestionsService
    from app.field_detection.providers.local import LocalFieldDetectionProvider

    monkeypatch.setattr(settings, "PDF_EXPORT_DIRECTORY", str(tmp_path / "exports"))

    form_pdf = tmp_path / "wohnungsgeber_form.pdf"
    doc_fitz = fitz.open()
    page = doc_fitz.new_page(width=595, height=842)
    page.insert_text(
        fitz.Point(70, 84),
        "Wohnungsgeberbestätigung zur Vorlage bei der Meldebehörde",
        fontsize=12,
    )
    page.insert_text(
        fitz.Point(90, 125),
        "Einzugsbestätigung des Wohnungsgebers",
        fontsize=10,
    )
    page.insert_text(
        fitz.Point(90, 143),
        "Auszugsbestätigung des Wohnungsgebers",
        fontsize=10,
    )
    page.insert_text(fitz.Point(70, 212), "In die Wohnung ist am", fontsize=10)
    page.insert_text(fitz.Point(70, 255), "1.", fontsize=10)
    page.insert_text(fitz.Point(70, 372), "Wohnungsgeber/-in", fontsize=11)
    page.insert_text(fitz.Point(70, 390), "Zuname, Vorname", fontsize=9)
    page.insert_text(fitz.Point(70, 515), "Eigentümer/-in der Wohnung", fontsize=11)
    page.insert_text(fitz.Point(70, 533), "Zuname, Vorname", fontsize=9)

    def _add_widget(name: str, wtype: int, rect: fitz.Rect) -> None:
        w = fitz.Widget()
        w.field_name = name
        w.field_type = wtype
        w.rect = rect
        page.add_widget(w)

    _add_widget("chkEinzug", fitz.PDF_WIDGET_TYPE_CHECKBOX, fitz.Rect(68, 115, 80, 127))
    _add_widget("chkAuszug", fitz.PDF_WIDGET_TYPE_CHECKBOX, fitz.Rect(68, 133, 80, 145))
    _add_widget(
        "txtDatumEinzug", fitz.PDF_WIDGET_TYPE_TEXT, fitz.Rect(200, 200, 360, 220)
    )
    _add_widget("txtPerson1", fitz.PDF_WIDGET_TYPE_TEXT, fitz.Rect(90, 244, 480, 264))
    _add_widget("txtNameGeber", fitz.PDF_WIDGET_TYPE_TEXT, fitz.Rect(70, 400, 480, 420))
    _add_widget("txtNameEigen", fitz.PDF_WIDGET_TYPE_TEXT, fitz.Rect(70, 544, 480, 564))
    doc_fitz.save(str(form_pdf))
    doc_fitz.close()

    db = SessionLocal()
    try:
        doc_service = SourceDocumentService(db)
        src_doc, doc_token = doc_service.upload_and_analyze(
            filename="wohnungsgeber_form.pdf",
            content_type="application/pdf",
            file_chunks=[form_pdf.read_bytes()],
            privacy_accepted=True,
            user_language="en",
            output_language="de",
        )
        assert src_doc.document_type == "fillable_pdf"
        assert src_doc.analysis_result["next_step"] == "dynamic_field_detection"

        prep_service = PrepareQuestionsService(
            db,
            ai_provider=MockAIProvider(),
            field_detection_provider=LocalFieldDetectionProvider(),
        )
        prep_res = await prep_service.prepare(src_doc.public_id, doc_token, "de", "de")
        assert prep_res.status == "ready"
        assert prep_res.session is not None
        assert prep_res.ownership_token is not None

        session = prep_res.session
        sess_token = prep_res.ownership_token
        fields_by_key = {f.key: f for f in session.version.fields}

        assert "txtperson1" in fields_by_key
        assert "txtdatumeinzug" in fields_by_key
        assert fields_by_key["txtdatumeinzug"].field_type == "date"

        labels_de = {
            f.key: next(t.label for t in f.translations if t.language == "de")
            for f in session.version.fields
        }
        assert labels_de["txtperson1"] == "Person 1"
        assert "Wohnungsgeber" in labels_de["txtnamegeber"]
        assert "Eigentümer" in labels_de["txtnameeigen"]

        for f in session.version.fields:
            if f.field_type in ("single_choice", "multiple_choice"):
                val: object = ["Einzugsbestätigung des Wohnungsgebers"]
                out_str = "Einzugsbestätigung des Wohnungsgebers"
            elif f.key == "txtdatumeinzug":
                val = "2026-11-01"
                out_str = "01.11.2026"
            elif f.key == "txtperson1":
                val = "Max Mustermann"
                out_str = "Max Mustermann"
            elif f.key == "txtnamegeber":
                val = "Anna Vermieterin"
                out_str = "Anna Vermieterin"
            else:
                val = "Karl Eigentümer"
                out_str = "Karl Eigentümer"

            db.add(
                FormAnswer(
                    session_id=session.id,
                    field_id=f.id,
                    original_answer=out_str,
                    original_language="de",
                    normalized_value=val,
                    output_value=out_str,
                    status="confirmed",
                    confirmed_by_user=True,
                )
            )
        session.status = "ready_for_export"
        db.commit()

        pdf_dir = tmp_path / "fixtures" / "pdf"
        pdf_dir.mkdir(parents=True, exist_ok=True)
        pdf_service = PDFExportService(db, pdf_dir)
        export = pdf_service.create_export(session.public_id, sess_token)
        assert export.status == "completed"

        export_path = Path(export.storage_path)
        assert export_path.is_file()
        rendered_doc = fitz.open(str(export_path))
        try:
            extracted_text = rendered_doc[0].get_text("text")
        finally:
            rendered_doc.close()
        assert "Max Mustermann" in extracted_text
        assert "Anna Vermieterin" in extracted_text
        assert "Karl Eigentümer" in extracted_text

        doc_service.storage.delete_file(src_doc.storage_path)
    finally:
        db.close()
