import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.answers.normalization.normalization import normalize_value
from app.answers.validation.validation import validate_value
from app.database.session import SessionLocal
from app.forms.models import (
    FormField,
    FormFieldOption,
    FormFieldOptionTranslation,
    FormFieldTranslation,
    FormTemplate,
    FormVersion,
)
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db() -> None:
    client.cookies.clear()
    client.headers.pop("X-CSRF-Token", None)
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.execute(text("TRUNCATE TABLE learned_form_patterns CASCADE"))
        db.execute(text("TRUNCATE TABLE users CASCADE"))
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


def test_country_choice_and_number_normalization_and_validation() -> None:
    assert normalize_value("country", "German") == "DE"
    assert normalize_value("country", "Deutsch") == "DE"
    assert normalize_value("country", "Deutschland") == "DE"
    assert normalize_value("country", "Türkei") == "TR"
    assert normalize_value("country", "سوريا") == "SY"
    assert normalize_value("country", "French") == "FR"
    assert normalize_value("country", "de") == "DE"

    ok_de, err_de = validate_value("country", "DE", True, {})
    assert ok_de is True and err_de is None
    ok_bad, _ = validate_value("country", "MARS", True, {})
    assert ok_bad is False

    assert normalize_value("choice", "  ja ") == "ja"
    ok_choice, _ = validate_value(
        "choice", "ja", True, {"options": [{"value": "ja"}, {"value": "nein"}]}
    )
    assert ok_choice is True
    bad_choice, _ = validate_value(
        "choice", "maybe", True, {"options": [{"value": "ja"}, {"value": "nein"}]}
    )
    assert bad_choice is False

    assert normalize_value("number", "42") == 42
    assert normalize_value("number", "12,5") == 12.5
    ok_num, _ = validate_value("number", 12.5, True, {})
    assert ok_num is True
    bad_num, _ = validate_value("number", "abc", True, {})
    assert bad_num is False


def _seed_multitable_version() -> str:
    db = SessionLocal()
    try:
        tmpl = FormTemplate(
            id=str(uuid.uuid4()),
            key=f"wbs-table-{uuid.uuid4().hex[:8]}",
            name="WBS Household Test",
            category="housing",
        )
        db.add(tmpl)
        db.flush()

        ver = FormVersion(
            id=str(uuid.uuid4()),
            form_template_id=tmpl.id,
            version_number=1,
            status="published",
            source_language="en",
            supported_output_languages=["en", "de"],
            origin="predefined_template",
        )
        db.add(ver)
        db.flush()

        pos = 0
        for row_idx in range(1, 4):
            row_role = "applicant" if row_idx == 1 else "member"
            row_label = "Applicant" if row_idx == 1 else f"Member {row_idx}"
            req = "required" if row_idx == 1 else "optional"

            # Vertically offset cell 1 in Row 1 (y=520 vs y=500) to prove explicit config overrides 10pt geometry
            name_y = 520.0 if row_idx == 1 else 500.0 + (row_idx - 1) * 30.0
            other_y = 500.0 + (row_idx - 1) * 30.0

            cols = [
                (
                    "name",
                    "Full name",
                    "string",
                    [20.0, name_y, 160.0, name_y + 18.0],
                    req,
                ),
                (
                    "birth_date",
                    "Date of birth",
                    "date",
                    [165.0, other_y, 240.0, other_y + 18.0],
                    req,
                ),
                (
                    "nationality",
                    "Nationality",
                    "country",
                    [245.0, other_y, 330.0, other_y + 18.0],
                    req,
                ),
                (
                    "own_income",
                    "Own income",
                    "single_choice",
                    [335.0, other_y, 430.0, other_y + 18.0],
                    "optional",
                ),
            ]
            for col_idx, (c_key, c_hdr, ftype, bbox, c_req) in enumerate(cols):
                fld = FormField(
                    id=str(uuid.uuid4()),
                    form_version_id=ver.id,
                    key=f"hh_{row_idx}_{c_key}",
                    field_type=ftype,
                    required=(c_req == "required"),
                    requiredness=c_req,
                    position=pos,
                    configuration={
                        "page": 1,
                        "bbox": bbox,
                        "table": {
                            "table_key": "hh",
                            "table_title": "Household members",
                            "row_index": row_idx,
                            "total_rows": 3,
                            "row_label": row_label,
                            "row_role": row_role,
                            "col_index": col_idx,
                            "column_header": c_hdr,
                        },
                    },
                )
                db.add(fld)
                db.flush()
                db.add(
                    FormFieldTranslation(
                        form_field_id=fld.id,
                        language="en",
                        label=c_hdr,
                    )
                )
                if ftype == "single_choice":
                    for o_i, (o_val, o_lbl) in enumerate(
                        [("ja", "Yes"), ("nein", "No")], start=1
                    ):
                        opt = FormFieldOption(
                            form_field_id=fld.id, value=o_val, position=o_i
                        )
                        db.add(opt)
                        db.flush()
                        db.add(
                            FormFieldOptionTranslation(
                                form_field_option_id=opt.id, language="en", label=o_lbl
                            )
                        )
                pos += 1

        db.commit()
        return ver.id
    finally:
        db.close()


def test_table_row_batch_submit_skip_and_navigation() -> None:
    version_id = _seed_multitable_version()

    sess_res = client.post(
        f"/api/form-versions/{version_id}/sessions",
        json={"userLanguage": "en", "outputLanguage": "de"},
    )
    assert sess_res.status_code == 201
    session_id = sess_res.json()["sessionId"]
    token = sess_res.json()["ownershipToken"]
    headers = {"X-Session-Token": token}

    start_res = client.post(f"/api/form-sessions/{session_id}/start", headers=headers)
    assert start_res.status_code == 200

    # 1. Fetch current field -> Row 1 has all 4 columns (incl. offset Cell 1) + fieldId + rowsOverview
    cur_res = client.get(
        f"/api/form-sessions/{session_id}/current-field", headers=headers
    )
    assert cur_res.status_code == 200
    body = cur_res.json()
    tbl = body["tableRow"]
    assert tbl["rowIndex"] == 1
    assert tbl["totalRows"] == 3
    assert [f["label"] for f in tbl["fields"]] == [
        "Full name",
        "Date of birth",
        "Nationality",
        "Own income",
    ]
    assert all(f["fieldId"] for f in tbl["fields"])
    assert len(tbl["rowsOverview"]) == 3

    fields_by_col = {f["fieldKey"]: f["fieldId"] for f in tbl["fields"]}

    # 2. Invalid date & unknown country return structured fieldErrors (NOT generic 422 "validation")
    bad_submit = client.post(
        f"/api/form-sessions/{session_id}/table-rows/submit",
        headers=headers,
        json={
            "items": [
                {"fieldId": fields_by_col["hh_1_name"], "value": "Ada Lovelace"},
                {"fieldId": fields_by_col["hh_1_birth_date"], "value": "99/99/1990"},
                {"fieldId": fields_by_col["hh_1_nationality"], "value": "Neverland"},
                {"fieldId": fields_by_col["hh_1_own_income"], "value": ""},
            ]
        },
    )
    assert bad_submit.status_code == 200
    bad_data = bad_submit.json()
    assert bad_data["status"] == "validation_error"
    err_codes = {e["fieldKey"]: e["reasonCode"] for e in bad_data["fieldErrors"]}
    assert err_codes["hh_1_birth_date"] == "invalid_date"
    assert err_codes["hh_1_nationality"] == "invalid_country"

    # 3. Valid Row 1 with demonym "German" + choice "ja" + blank optional auto-skip? wait fill "ja"
    good_submit = client.post(
        f"/api/form-sessions/{session_id}/table-rows/submit",
        headers=headers,
        json={
            "items": [
                {"fieldId": fields_by_col["hh_1_name"], "value": "Ada Lovelace"},
                {"fieldId": fields_by_col["hh_1_birth_date"], "value": "10.12.1990"},
                {"fieldId": fields_by_col["hh_1_nationality"], "value": "German"},
                {"fieldId": fields_by_col["hh_1_own_income"], "value": "ja"},
            ]
        },
    )
    assert good_submit.status_code == 200
    assert good_submit.json()["status"] == "ok"
    assert good_submit.json()["submittedCount"] == 4

    # 4. Jump directly to Row 3 via ?field_id= and verify it opens Row 3
    row3_first_id = tbl["rowsOverview"][2]["firstFieldId"]
    jump_res = client.get(
        f"/api/form-sessions/{session_id}/current-field?field_id={row3_first_id}",
        headers=headers,
    )
    assert jump_res.status_code == 200
    assert jump_res.json()["tableRow"]["rowIndex"] == 3

    # 5. Jump to Row 2 and skip remaining empty rows (Row 2 + Row 3)
    row2_first_id = tbl["rowsOverview"][1]["firstFieldId"]
    j2 = client.get(
        f"/api/form-sessions/{session_id}/current-field?field_id={row2_first_id}",
        headers=headers,
    )
    assert j2.status_code == 200
    row2_ids = [f["fieldId"] for f in j2.json()["tableRow"]["fields"]]

    skip_res = client.post(
        f"/api/form-sessions/{session_id}/table-rows/skip",
        headers=headers,
        json={
            "fieldIds": row2_ids,
            "skipRemainingEmptyRows": True,
            "tableKey": "hh",
            "fromRowIndex": 2,
        },
    )
    assert skip_res.status_code == 200
    assert skip_res.json()["skippedCount"] == 8  # Row 2 (4) + Row 3 (4)
