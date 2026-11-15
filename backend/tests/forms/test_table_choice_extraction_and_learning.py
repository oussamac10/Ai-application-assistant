import uuid

import fitz
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database.session import SessionLocal
from app.forms.learning_models import LearnedFormPattern
from app.forms.models import FormTemplate, FormVersion
from app.forms.pdf_field_extractor import (
    extract_fields_from_pdf_bytes,
    insert_extracted_fields,
)
from app.main import app
from app.pdf.dynamic_overlay import render_form_version_overlay_pdf
from app.sessions.services import SessionService

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db() -> None:
    client.cookies.clear()
    client.headers.pop("X-CSRF-Token", None)
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.execute(text("TRUNCATE TABLE organizations CASCADE"))
        db.execute(text("TRUNCATE TABLE learned_form_patterns CASCADE"))
        db.execute(text("TRUNCATE TABLE users CASCADE"))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def _build_stuttgart_like_wbs_pdf() -> bytes:
    """Create a synthetic AcroForm PDF with horizontal choices + a 3-row household table."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    # 1. Standalone horizontal choice cluster: Familienstand
    page.insert_text((40, 115), "Familienstand", fontsize=10)
    fam_opts = [("ledig", 45), ("verheiratet", 130), ("geschieden", 230)]
    for opt_lbl, x_pos in fam_opts:
        w = fitz.Widget()
        w.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
        w.field_name = f"chk_{opt_lbl}"
        w.rect = fitz.Rect(x_pos, 126, x_pos + 12, 138)
        page.add_widget(w)
        page.insert_text((x_pos + 16, 136), opt_lbl, fontsize=9)

    # 2. Household table: vector grid lines + header + Row 1 (offset Antragstellende Person) + Rows 2-3
    page.insert_text(
        (40, 210),
        "2 Haushaltsangehörige, die aufgenommen werden sollen",
        fontsize=10,
    )
    x_cols = [40, 200, 290, 360, 450, 555]
    y_rows = [225, 250, 290, 320, 350]
    for y in y_rows:
        page.draw_line((x_cols[0], y), (x_cols[-1], y))
    for x in x_cols:
        page.draw_line((x, y_rows[0]), (x, y_rows[-1]))

    headers = [
        ("Name, Vorname", 44),
        ("Geburtsdatum", 204),
        ("Geschlecht m/w/d", 294),
        ("Staatsangehörigkeit", 364),
        ("eigenes Einkommen", 454),
    ]
    for h_text, hx in headers:
        page.insert_text((hx, 240), h_text, fontsize=8)

    for row_idx in range(1, 4):
        ry0 = y_rows[row_idx]
        if row_idx == 1:
            page.insert_text((44, ry0 + 11), "Antragstellende Person", fontsize=8)
            name_rect = fitz.Rect(
                44, ry0 + 15, 194, ry0 + 34
            )  # Vertically offset inside Row 1!
        else:
            name_rect = fitz.Rect(44, ry0 + 6, 194, ry0 + 24)

        for cname, rect in [
            (f"name_{row_idx}", name_rect),
            (f"geb_{row_idx}", fitz.Rect(204, ry0 + 6, 285, ry0 + 24)),
            (f"sex_{row_idx}", fitz.Rect(294, ry0 + 6, 354, ry0 + 24)),
            (f"nat_{row_idx}", fitz.Rect(364, ry0 + 6, 444, ry0 + 24)),
        ]:
            w = fitz.Widget()
            w.field_type = fitz.PDF_WIDGET_TYPE_TEXT
            w.field_name = cname
            w.rect = rect
            page.add_widget(w)

        # Intra-row checkboxes: ja / nein
        for inc_lbl, ix in [("ja", 460), ("nein", 505)]:
            cw = fitz.Widget()
            cw.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
            cw.field_name = f"inc_{row_idx}_{inc_lbl}"
            cw.rect = fitz.Rect(ix, ry0 + 8, ix + 11, ry0 + 19)
            page.add_widget(cw)
            page.insert_text((ix + 14, ry0 + 17), inc_lbl, fontsize=8)

    buf = doc.tobytes()
    doc.close()
    return buf


def _register_org_admin(email: str) -> dict[str, str]:
    reg = client.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": "Password123!",
            "passwordConfirmation": "Password123!",
        },
    )
    assert reg.status_code == 201
    csrf = client.cookies.get("csrf_token") or ""
    headers = {"X-CSRF-Token": csrf}

    org_res = client.post(
        "/api/organizations",
        headers=headers,
        json={"name": "Stuttgart Housing Office", "organizationType": "authority"},
    )
    assert org_res.status_code in (200, 201)
    return headers


def test_table_per_row_extraction_option_box_overlay_and_row_isolation() -> None:
    pdf_bytes = _build_stuttgart_like_wbs_pdf()
    fields = extract_fields_from_pdf_bytes(pdf_bytes)

    fam_fields = [f for f in fields if "familienstand" in f["label"].lower()]
    assert len(fam_fields) == 1
    assert fam_fields[0]["field_type"] == "single_choice"
    assert len(fam_fields[0].get("option_boxes") or []) == 3

    table_fields = [f for f in fields if isinstance(f.get("table"), dict)]
    row1 = [f for f in table_fields if f["table"]["row_index"] == 1]
    row2 = [f for f in table_fields if f["table"]["row_index"] == 2]
    row3 = [f for f in table_fields if f["table"]["row_index"] == 3]

    # Offset Row 1 Name, Vorname is included in Row 1 alongside the other 4 columns
    assert len(row1) == 5
    assert len(row2) == 5
    assert len(row3) == 5
    assert row1[0]["table"]["row_role"] == "applicant"
    assert row2[0]["table"]["row_role"] == "member"

    # Gender shorthand header -> single_choice m/w/d; intra-row checkboxes -> single_choice ja/nein with option_boxes
    row1_sex = next(f for f in row1 if "geschlecht" in f["label"].lower())
    assert row1_sex["field_type"] == "single_choice"
    assert [o["value"] for o in row1_sex["options"]] == ["m", "w", "d"]

    row1_inc = next(f for f in row1 if "einkommen" in f["label"].lower())
    assert row1_inc["field_type"] == "single_choice"
    assert len(row1_inc["option_boxes"]) == 2

    # Nationality -> country; Row 1 may infer question_key, Rows 2 & 3 MUST remain None & optional
    row1_nat = next(f for f in row1 if "staatsangeh" in f["label"].lower())
    row2_nat = next(f for f in row2 if "staatsangeh" in f["label"].lower())
    assert row1_nat["field_type"] == "country"
    assert row1_nat["question_key"] == "personal.nationality"
    assert row2_nat["question_key"] is None
    assert row2_nat["requiredness"] == "optional"


def test_option_boxes_pdf_export_draws_mark_on_selected_option() -> None:
    pdf_bytes = _build_stuttgart_like_wbs_pdf()
    fields = extract_fields_from_pdf_bytes(pdf_bytes)

    db = SessionLocal()
    try:
        import tempfile
        from pathlib import Path

        from app.answers.models import FormAnswer
        from app.storage.factory import get_storage_provider

        storage = get_storage_provider()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = Path(tmp.name)
        try:
            stored_pdf = storage.save_file(
                "documents", f"wbs-{uuid.uuid4().hex[:6]}.pdf", tmp_path
            )
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

        tmpl = FormTemplate(
            id=str(uuid.uuid4()),
            key=f"wbs-exp-{uuid.uuid4().hex[:6]}",
            name="WBS Export Test",
        )
        db.add(tmpl)
        db.flush()

        ver = FormVersion(
            id=str(uuid.uuid4()),
            form_template_id=tmpl.id,
            version_number=1,
            status="published",
            source_language="de",
            supported_output_languages=["de"],
            origin="predefined_template",
            source_pdf_storage_path=stored_pdf,
        )
        db.add(ver)
        db.flush()

        insert_extracted_fields(db, ver.id, fields, source_language="de")
        db.commit()
        db.refresh(ver)

        session, _raw_token = SessionService(db).create_session(
            form_version_id=ver.id,
            user_language="de",
            output_language="de",
        )

        # Pick first row's income ("ja") and gender ("m")
        row1_inc = next(
            f
            for f in ver.fields
            if (f.configuration or {}).get("table", {}).get("row_index") == 1
            and "einkommen"
            in (f.configuration or {}).get("table", {}).get("column_header", "").lower()
        )
        row1_sex = next(
            f
            for f in ver.fields
            if (f.configuration or {}).get("table", {}).get("row_index") == 1
            and "geschlecht"
            in (f.configuration or {}).get("table", {}).get("column_header", "").lower()
        )
        ans_inc = FormAnswer(
            session_id=session.id,
            field_id=row1_inc.id,
            original_answer="ja",
            original_language="de",
            normalized_value="ja",
            output_value="ja",
            status="confirmed",
            validation_status="valid",
        )
        ans_sex = FormAnswer(
            session_id=session.id,
            field_id=row1_sex.id,
            original_answer="m",
            original_language="de",
            normalized_value="m",
            output_value="m",
            status="confirmed",
            validation_status="valid",
        )
        db.add(ans_inc)
        db.add(ans_sex)
        db.commit()

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as out_tmp:
            out_pdf_path = Path(out_tmp.name)
        try:
            render_form_version_overlay_pdf(
                session=session,
                version=ver,
                answers_by_field_id={row1_inc.id: ans_inc, row1_sex.id: ans_sex},
                output_path=out_pdf_path,
            )
            out_doc = fitz.open(out_pdf_path)
            out_page = out_doc[0]
            # Verify "m" text is drawn and "ja" checkbox tick path is drawn inside ja option bbox
            ja_box = next(
                b["bbox"]
                for b in (row1_inc.configuration or {})["option_boxes"]
                if b["value"] == "ja"
            )
            nein_box = next(
                b["bbox"]
                for b in (row1_inc.configuration or {})["option_boxes"]
                if b["value"] == "nein"
            )
            drawings = out_page.get_drawings()
            ja_rect = fitz.Rect(*ja_box).irect
            nein_rect = fitz.Rect(*nein_box).irect
            ja_hits = [
                d
                for d in drawings
                if d.get("rect")
                and ja_rect.intersects(d["rect"].irect)
                and d["rect"].width <= 20
            ]
            nein_hits = [
                d
                for d in drawings
                if d.get("rect")
                and nein_rect.intersects(d["rect"].irect)
                and d["rect"].width <= 20
            ]
            assert len(ja_hits) >= 1
            assert len(nein_hits) == 0
            out_doc.close()
        finally:
            if out_pdf_path.exists():
                out_pdf_path.unlink()
    finally:
        db.close()


def test_review_studio_combine_choice_sync_and_continual_learning() -> None:
    headers = _register_org_admin("curator@example.com")

    # 1. Create a PDF with two separated checkboxes so manual Shift-click combine in Studio learns
    doc2 = fitz.open()
    p2 = doc2.new_page()
    for idx, (lbl, y0) in enumerate(
        [("Vollzeitbeschaeftigung", 100), ("Teilzeitbeschaeftigung", 145)]
    ):
        w = fitz.Widget()
        w.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
        w.field_name = f"work_{idx}"
        w.rect = fitz.Rect(50, y0, 64, y0 + 14)
        p2.add_widget(w)
        p2.insert_text((68, y0 + 11), lbl, fontsize=10)
    pdf_sep = doc2.tobytes()
    doc2.close()

    up = client.post(
        "/api/organizations/current/forms/upload",
        headers=headers,
        data={"name": "Employment Form A", "auto_extract": "true"},
        files={"file": ("employment_a.pdf", pdf_sep, "application/pdf")},
    )
    assert up.status_code == 201
    form_a = up.json()
    field_ids = [f["id"] for f in form_a["fields"]]
    assert len(field_ids) == 2

    # 2. Studio user combines them into a single choice question
    combined = client.post(
        f"/api/organizations/current/forms/{form_a['templateId']}/fields/combine-choice",
        headers=headers,
        json={
            "fieldIds": field_ids,
            "label": "Beschäftigungsart",
            "fieldType": "single_choice",
            "requiredness": "required",
        },
    )
    assert combined.status_code == 200
    c_fields = combined.json()["fields"]
    assert len(c_fields) == 1
    assert c_fields[0]["fieldType"] == "single_choice"
    assert len(c_fields[0]["options"]) == 2
    assert len(c_fields[0]["configuration"]["option_boxes"]) == 2

    # 3. Also test table curation + publish -> Zero-PII LearnedFormPattern recorded
    pub = client.post(
        f"/api/organizations/current/forms/{form_a['templateId']}/publish",
        headers=headers,
    )
    assert pub.status_code == 200

    db = SessionLocal()
    try:
        patterns = db.query(LearnedFormPattern).all()
        assert len(patterns) >= 1
        assert any(p.pattern_type == "choice_group" for p in patterns)
    finally:
        db.close()

    # 4. Now upload WBS-style form, update Row 1 column type, and sync Row 1 -> Row 2..N
    wbs_pdf = _build_stuttgart_like_wbs_pdf()
    up_wbs = client.post(
        "/api/organizations/current/forms/upload",
        headers=headers,
        data={"name": "WBS Form 1", "auto_extract": "true"},
        files={"file": ("wbs1.pdf", wbs_pdf, "application/pdf")},
    )
    assert up_wbs.status_code == 201
    wbs_review = up_wbs.json()
    row1_sex = next(
        f
        for f in wbs_review["fields"]
        if (f.get("configuration") or {}).get("table", {}).get("row_index") == 1
        and "geschlecht" in f["translations"][0]["label"].lower()
    )
    t_key = row1_sex["configuration"]["table"]["table_key"]

    sync_res = client.post(
        f"/api/organizations/current/forms/{wbs_review['templateId']}/tables/{t_key}/sync-columns",
        headers=headers,
        json={"sourceRowIndex": 1},
    )
    assert sync_res.status_code == 200

    # Publish WBS Form 1 to reinforce table_schema pattern
    pub2 = client.post(
        f"/api/organizations/current/forms/{wbs_review['templateId']}/publish",
        headers=headers,
    )
    assert pub2.status_code == 200

    # 5. Re-upload similar WBS form -> learned_pattern_id & curated metadata automatically attach
    up_wbs2 = client.post(
        "/api/organizations/current/forms/upload",
        headers=headers,
        data={"name": "WBS Form 2", "auto_extract": "true"},
        files={"file": ("wbs2.pdf", wbs_pdf, "application/pdf")},
    )
    assert up_wbs2.status_code == 201
    wbs2_fields = up_wbs2.json()["fields"]
    learned_hits = [
        f
        for f in wbs2_fields
        if (f.get("configuration") or {}).get("learned_pattern_id")
    ]
    assert len(learned_hits) >= 5
    # Verify secondary rows STILL have zero Vault key leakage even after pattern learning
    row2_hits = [
        f
        for f in wbs2_fields
        if (f.get("configuration") or {}).get("table", {}).get("row_index", 1) >= 2
    ]
    assert row2_hits
    assert all(f["questionKey"] is None for f in row2_hits)
