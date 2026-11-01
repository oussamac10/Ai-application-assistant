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
            "y": 263.5,
            "width": 120.0,
            "height": 14.5,
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


@pytest.mark.asyncio
async def test_french_flattened_pdf_end_to_end_prepare_and_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end test for `fixtures/pdf/required-optional-validation-fr.pdf`:
    - Full-width single-column underline fields (`Adresse complete`, `Adresse e-mail`,
      `Intitule de la formation`) are detected alongside 2-column underline fields
    - Standalone option groups (`Statut professionnel`, `Methode de contact preferee`)
      and choice groups (`Genre`, `Cochez les documents fournis`, `Langues preferees`)
      mark their vector checkbox/radio squares instead of printing text over options
    - Declaration boolean fields (`Je certifie...`, `J'accepte...`, `Je souhaite...`)
      check only `True` boxes and never print `"Yes"` / `"No"` text on the page.
    """
    from app.ai.mock_provider import MockAIProvider
    from app.core.config import settings
    from app.documents.service import SourceDocumentService
    from app.field_detection.orchestration import PrepareQuestionsService
    from app.field_detection.providers.local import LocalFieldDetectionProvider

    monkeypatch.setattr(settings, "PDF_EXPORT_DIRECTORY", str(tmp_path / "exports"))

    fixture_pdf = (
        Path(__file__).resolve().parents[3]
        / "fixtures"
        / "pdf"
        / "required-optional-validation-fr.pdf"
    )
    if not fixture_pdf.is_file():
        fixture_pdf = Path("/fixtures/pdf/required-optional-validation-fr.pdf")
    assert fixture_pdf.is_file()

    db = SessionLocal()
    try:
        doc_service = SourceDocumentService(db)
        src_doc, doc_token = doc_service.upload_and_analyze(
            filename="required-optional-validation-fr.pdf",
            content_type="application/pdf",
            file_chunks=[fixture_pdf.read_bytes()],
            privacy_accepted=True,
            user_language="en",
            output_language="fr",
        )
        prep_service = PrepareQuestionsService(
            db,
            ai_provider=MockAIProvider(),
            field_detection_provider=LocalFieldDetectionProvider(),
        )
        prep_res = await prep_service.prepare(src_doc.public_id, doc_token, "en", "fr")
        assert prep_res.status == "ready"
        assert prep_res.session is not None
        assert prep_res.ownership_token is not None

        session = prep_res.session
        sess_token = prep_res.ownership_token
        fields_by_key = {f.key: f for f in session.version.fields}

        # Verify full-width marked underlines are detected
        assert "adresse_complete" in fields_by_key
        assert "adresse_e_mail" in fields_by_key
        assert "intitule_de_la_formation" in fields_by_key
        assert "statut_professionnel" in fields_by_key

        for f in session.version.fields:
            if f.key == "nom_de_famille":
                val: object = "Alaoui"
                out_str = "Alaoui"
            elif f.key == "prenom":
                val = "Youssef"
                out_str = "Youssef"
            elif f.key == "adresse_complete":
                val = "12 Rue de Rivoli"
                out_str = "12 Rue de Rivoli"
            elif f.key == "adresse_e_mail":
                val = "youssef@example.org"
                out_str = "youssef@example.org"
            elif f.key == "intitule_de_la_formation":
                val = "Ingénierie Logicielle"
                out_str = "Ingénierie Logicielle"
            elif f.key == "genre":
                val = "Homme"
                out_str = "Homme"
            elif f.key == "statut_professionnel":
                val = "Salarie(e)"
                out_str = "Salarie(e)"
            elif f.field_type == "single_choice":
                opts = (f.configuration or {}).get("options") or []
                first_val = opts[0]["value"] if opts else "Option"
                val = first_val
                out_str = first_val
            elif f.field_type == "multiple_choice":
                opts = (f.configuration or {}).get("options") or []
                picked = [opts[0]["value"]] if opts else []
                val = picked
                out_str = ", ".join(picked)
            elif f.field_type == "boolean":
                # Mix True and False to ensure neither prints "Yes" or "No"
                is_true = "certifie" in f.key or "accepte" in f.key
                val = is_true
                out_str = "Yes" if is_true else "No"
            elif f.field_type == "signature":
                val = {
                    "width": 300,
                    "height": 100,
                    "strokes": [
                        [
                            [20.0, 50.0],
                            [150.0, 30.0],
                            [270.0, 60.0],
                        ]
                    ],
                }
                out_str = "Signed"
            else:
                val = f"Val-{f.position}"
                out_str = f"Val-{f.position}"

            db.add(
                FormAnswer(
                    session_id=session.id,
                    field_id=f.id,
                    original_answer=out_str,
                    original_language="fr",
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
            p1_text = rendered_doc[0].get_text("text")
            p2_text = rendered_doc[1].get_text("text")
        finally:
            rendered_doc.close()

        # Underlined text fields on page 1 and page 2 are rendered into the PDF
        assert "Alaoui" in p1_text
        assert "Youssef" in p1_text
        assert "12 Rue de Rivoli" in p1_text
        assert "youssef@example.org" in p1_text
        assert "Ingénierie Logicielle" in p2_text

        # Choice fields ("Homme", "Salarie(e)") must mark vector squares and NOT
        # print a second copy of the option text over the page
        assert p1_text.count("Homme") == 1
        assert p1_text.count("Salarie(e)") == 1

        # Boolean fields must never print literal "Yes" or "No" on page 2
        assert "Yes" not in p2_text
        assert "No" not in p2_text

        doc_service.storage.delete_file(src_doc.storage_path)
    finally:
        db.close()


@pytest.mark.asyncio
async def test_german_rental_contract_pdf_end_to_end_prepare_and_export(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """End-to-end test for `fixtures/pdf/rental-contract-de.pdf` (`Mietvertrag`):
    - Dotted-line (`…………`) and underscore (`________`) fields in `_detect_normal_fields`
      receive `input_bounding_box` coordinates and render on Page 1 and Page 2
    - Long keys (>64 chars, e.g. `anzahl_der_untergebrachten_personen_...`) match
      between `question_bridge` and `dynamic_overlay`
    - Inline blank fields (`beginnt am ____ und endet am ____`, `beträgt ____ Euro.`)
      render inside the blank gap without duplicating `EUR Euro.`.
    """
    from app.ai.mock_provider import MockAIProvider
    from app.core.config import settings
    from app.documents.service import SourceDocumentService
    from app.field_detection.orchestration import PrepareQuestionsService
    from app.field_detection.providers.local import LocalFieldDetectionProvider

    monkeypatch.setattr(settings, "PDF_EXPORT_DIRECTORY", str(tmp_path / "exports"))

    fixture_pdf = (
        Path(__file__).resolve().parents[3]
        / "fixtures"
        / "pdf"
        / "rental-contract-de.pdf"
    )
    if not fixture_pdf.is_file():
        fixture_pdf = Path("/fixtures/pdf/rental-contract-de.pdf")
    assert fixture_pdf.is_file()

    db = SessionLocal()
    try:
        doc_service = SourceDocumentService(db)
        src_doc, doc_token = doc_service.upload_and_analyze(
            filename="rental-contract-de.pdf",
            content_type="application/pdf",
            file_chunks=[fixture_pdf.read_bytes()],
            privacy_accepted=True,
            user_language="en",
            output_language="de",
        )
        prep_service = PrepareQuestionsService(
            db,
            ai_provider=MockAIProvider(),
            field_detection_provider=LocalFieldDetectionProvider(),
        )
        prep_res = await prep_service.prepare(src_doc.public_id, doc_token, "en", "de")
        assert prep_res.status == "ready"
        assert prep_res.session is not None
        assert prep_res.ownership_token is not None

        session = prep_res.session
        sess_token = prep_res.ownership_token

        for f in session.version.fields:
            if f.key == "vermieter_name":
                val: object = "Hans Vermieter"
                out_str = "Hans Vermieter"
            elif f.key == "vermieter_stra_e_nr":
                val = "Hauptstr. 10, Stuttgart"
                out_str = "Hauptstr. 10, Stuttgart"
            elif f.key == "mieter_name":
                val = "Oussama Chajii"
                out_str = "Oussama Chajii"
            elif "im_haus" in f.key:
                val = "Stuttgart Landhausstr. 250"
                out_str = "Stuttgart Landhausstr. 250"
            elif f.field_type == "integer":
                val = 3
                out_str = "3"
            elif f.field_type == "date":
                val = "2026-05-01"
                out_str = "01.05.2026"
            elif f.field_type == "money":
                val = {"amount": 1200, "currency": "EUR", "period": "monthly"}
                out_str = "1200 EUR monthly"
            elif f.key == "mietkosten_iban":
                val = "DE89370400440532013000"
                out_str = "DE89370400440532013000"
            else:
                val = f"Test-{f.position}"
                out_str = f"Test-{f.position}"

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
            p1_text = rendered_doc[0].get_text("text")
            p2_text = rendered_doc[1].get_text("text")
        finally:
            rendered_doc.close()

        assert "Hans Vermieter" in p1_text
        assert "Hauptstr. 10, Stuttgart" in p1_text
        assert "Oussama Chajii" in p1_text
        assert "Stuttgart Landhausstr. 250" in p1_text
        assert "01.05.2026" in p2_text
        assert "1,200" in p2_text
        assert "DE89370400440532013000" in p2_text
        assert "EUR Euro." not in p2_text
        assert "monthly Euro." not in p2_text

        ans_service = AnswerService(db)
        png_bytes = ans_service.get_page_preview_png(session.public_id, 1, sess_token)
        assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"

        doc_service.storage.delete_file(src_doc.storage_path)
    finally:
        db.close()


def test_clarification_merges_address_parts_instead_of_dict_repr() -> None:
    """Regression test: submitting clarification `{'city': 'Stuttgart'}` for an
    address field with `original_answer='Landhausstrasse 260, 70188'` must
    produce `'Landhausstrasse 260, 70188, Stuttgart'`, never `\"{'city': 'Stuttgart'}\"`.
    """
    db = SessionLocal()
    try:
        token = "clarify-address-token"
        token_hash = hash_ownership_token(token)
        expires = datetime.now(UTC) + timedelta(hours=2)

        template = FormTemplate(key="clarify-addr-tpl", name="Clarify Addr")
        db.add(template)
        db.commit()

        version = FormVersion(
            form_template_id=template.id,
            version_number=1,
            status="published",
            source_language="de",
            supported_output_languages=["de", "en"],
        )
        db.add(version)
        db.commit()

        addr_field = FormField(
            form_version_id=version.id,
            key="anschrift",
            field_type="address",
            required=True,
            requiredness="required",
            position=0,
        )
        name_field = FormField(
            form_version_id=version.id,
            key="wohnungsgeber_name",
            field_type="string",
            required=True,
            requiredness="required",
            position=1,
        )
        db.add_all([addr_field, name_field])
        db.commit()

        session = FormSession(
            form_version_id=version.id,
            user_language="en",
            source_language="de",
            output_language="de",
            ownership_token_hash=token_hash,
            status="in_progress",
            expires_at=expires,
        )
        db.add(session)
        db.commit()

        addr_ans = FormAnswer(
            session_id=session.id,
            field_id=addr_field.id,
            original_answer="Landhausstrasse 260, 70188",
            original_language="en",
            normalized_value="Landhausstrasse 260, 70188",
            status="needs_clarification",
            requires_clarification=True,
        )
        gibberish_ans = FormAnswer(
            session_id=session.id,
            field_id=name_field.id,
            original_answer="knjdgksj iengioew",
            original_language="en",
            normalized_value="knjdgksj iengioew",
            status="needs_clarification",
            requires_clarification=True,
        )
        db.add_all([addr_ans, gibberish_ans])
        db.commit()

        service = AnswerService(db)
        updated_addr = service.submit_clarification(
            session.public_id,
            addr_ans.id,
            {"city": "Stuttgart"},
            token,
        )
        assert updated_addr.status == "awaiting_confirmation"
        assert updated_addr.output_value == "Landhausstrasse 260, 70188, Stuttgart"
        assert "{" not in (updated_addr.output_value or "")

        updated_name = service.submit_clarification(
            session.public_id,
            gibberish_ans.id,
            {
                "The user answer 'knjdgksj iengioew' is gibberish and does not represent a valid name.": "Oussama Chajii"
            },
            token,
        )
        assert updated_name.status == "awaiting_confirmation"
        assert updated_name.output_value == "Oussama Chajii"
        assert "{" not in (updated_name.output_value or "")
    finally:
        db.close()


@pytest.mark.asyncio
async def test_ocr_field_without_input_box_scales_label_bounding_box_to_pdf_points(
    tmp_path: Path,
) -> None:
    from app.forms.models import FormFieldTranslation
    from app.ocr.models import OCRPage, OCRResult

    db = SessionLocal()
    try:
        uploaded_pdf = _create_blank_uploaded_pdf(tmp_path)
        token = "ocr-scale-preview-token"
        token_hash = hash_ownership_token(token)
        expires = datetime.now(UTC) + timedelta(hours=2)

        source_doc = SourceDocument(
            ownership_token_hash=token_hash,
            original_filename="3_scanned_form_image.png",
            sanitized_filename="3_scanned_form_image.pdf",
            storage_path=str(uploaded_pdf),
            content_type="application/pdf",
            size_bytes=uploaded_pdf.stat().st_size,
            checksum_sha256="c" * 64,
            status="analyzed",
            page_count=1,
            expires_at=expires,
        )
        db.add(source_doc)
        db.commit()

        ocr_res = OCRResult(
            source_document_id=source_doc.id,
            status="completed",
            provider_name="local",
            language="auto",
            page_count=1,
            expires_at=expires,
        )
        db.add(ocr_res)
        db.commit()
        db.add(
            OCRPage(
                ocr_result_id=ocr_res.id,
                page_number=1,
                width=2480,
                height=3509,
                text="Nachname *:",
                average_confidence=92.0,
                lines=[],
            )
        )
        db.commit()

        detection = FieldDetectionResult(
            source_document_id=source_doc.id,
            ocr_result_id=ocr_res.id,
            status="completed",
            provider_name="local",
            analysis_version=1,
            field_count=1,
            expires_at=expires,
        )
        db.add(detection)
        db.commit()

        db.add(
            DetectedField(
                detection_result_id=detection.id,
                page_number=1,
                display_order=0,
                label="Nachname *",
                normalized_name="nachname",
                field_type="text",
                required=True,
                confidence=0.85,
                source="ocr",
                label_bounding_box={
                    "x": 233.0,
                    "y": 737.0,
                    "width": 259.0,
                    "height": 36.0,
                },
                input_bounding_box=None,
                review_status="confirmed",
            )
        )
        db.commit()

        template = FormTemplate(
            key=f"dynamic-doc-{source_doc.public_id}",
            name="Dynamic form — scan",
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
        )
        db.add(version)
        db.commit()

        f_last = FormField(
            form_version_id=version.id,
            key="nachname",
            field_type="string",
            required=True,
            requiredness="required",
            position=0,
        )
        db.add(f_last)
        db.commit()
        db.add(
            FormFieldTranslation(
                form_field_id=f_last.id,
                language="en",
                label="Last name",
            )
        )
        db.commit()

        session = FormSession(
            form_version_id=version.id,
            source_document_id=source_doc.id,
            source_language="de",
            user_language="en",
            output_language="de",
            status="in_progress",
            ownership_token_hash=token_hash,
            expires_at=expires,
        )
        db.add(session)
        db.commit()

        service = AnswerService(db)
        current = await service.get_current_field(session.public_id, token)
        box = current["input_bounding_box"]
        assert box is not None
        # 737 / 3509 * 842 ≈ 176.85 pt (21% down the page), NOT 737 pt (87.5%)!
        assert box["y"] == pytest.approx(737.0 * (842.0 / 3509.0), abs=1.5)
        assert box["x"] == pytest.approx(233.0 * (595.0 / 2480.0), abs=1.5)
    finally:
        db.close()
