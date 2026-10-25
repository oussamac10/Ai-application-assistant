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
