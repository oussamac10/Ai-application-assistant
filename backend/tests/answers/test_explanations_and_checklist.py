from collections.abc import Generator
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.answers.explanations import (
    build_submission_checklist,
    resolve_field_explanation,
)
from app.answers.states import PENDING_MANUAL_SIGNATURE
from app.database.session import SessionLocal
from app.forms.schemas import FieldCreate, TranslationSchema
from app.forms.services import FormService
from app.main import app
from app.sessions.services import SessionService

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.commit()
        yield
    except Exception:
        db.rollback()
    finally:
        db.close()


def _dummy_field(
    *,
    key: str = "custom_field",
    question_key: str | None = None,
    field_type: str = "string",
    source_label: str = "Custom Field",
    source_language: str = "de",
) -> Any:
    return SimpleNamespace(
        key=key,
        question_key=question_key,
        field_type=field_type,
        version=SimpleNamespace(source_language=source_language),
        translations=[SimpleNamespace(language=source_language, label=source_label)],
    )


def test_resolve_field_explanation_by_semantic_key_all_languages() -> None:
    field = _dummy_field(
        key="birth_date",
        question_key="personal.date_of_birth",
        field_type="date",
        source_label="Geburtsdatum",
    )
    for lang in ("en", "de", "fr", "ar"):
        exp = resolve_field_explanation(field, "Date of Birth", lang)
        assert exp["summary"]
        assert exp["where_to_find"]
        assert exp["example"] == "15.09.2000"


def test_resolve_field_explanation_by_bureaucratic_keyword() -> None:
    landlord_field = _dummy_field(
        key="wohnungsgeber_name_anschrift",
        field_type="string",
        source_label="Name und Anschrift des Wohnungsgebers",
    )
    exp_en = resolve_field_explanation(
        landlord_field, "Name and address of landlord", "en"
    )
    assert "landlord" in exp_en["summary"].lower()
    assert "rental contract" in exp_en["where_to_find"].lower()

    move_in_field = _dummy_field(
        key="am_einzug_datum",
        field_type="date",
        source_label="Einzug am",
    )
    exp_ar = resolve_field_explanation(move_in_field, "تاريخ الانتقال", "ar")
    assert "انتقال" in exp_ar["summary"]
    assert exp_ar["example"] == "01.11.2026"


def test_resolve_field_explanation_fallback_by_field_type() -> None:
    unknown_field = _dummy_field(
        key="unusual_reference_code",
        field_type="string",
        source_label="Unusual Reference Code",
    )
    exp = resolve_field_explanation(unknown_field, "Unusual Reference Code", "fr")
    assert "formulaire officiel" in exp["summary"]
    assert exp["where_to_find"]
    assert exp["example"]


def test_build_submission_checklist_includes_contextual_items() -> None:
    f1 = SimpleNamespace(
        id="f1",
        key="wohnungsgeber_name",
        question_key=None,
        field_type="string",
        translations=[SimpleNamespace(language="de", label="Name des Wohnungsgebers")],
    )
    f2 = SimpleNamespace(
        id="f2",
        key="iban",
        question_key=None,
        field_type="string",
        translations=[SimpleNamespace(language="de", label="IBAN")],
    )
    f3 = SimpleNamespace(
        id="f3",
        key="unterschrift",
        question_key=None,
        field_type="signature",
        translations=[SimpleNamespace(language="de", label="Unterschrift")],
    )
    version = SimpleNamespace(source_language="de", fields=[f1, f2, f3])
    answers = {
        "f3": SimpleNamespace(status=PENDING_MANUAL_SIGNATURE),
    }

    checklist = build_submission_checklist(version, answers, "en")
    ids = [item["id"] for item in checklist]
    assert "review_printed_values" in ids
    assert "manual_signature_required" in ids
    assert "landlord_counter_signature" in ids
    assert "verify_bank_details" in ids
    assert "identity_document_check" in ids


def test_current_field_and_summary_routes_include_explanation_and_checklist() -> None:
    db = SessionLocal()
    try:
        form_service = FormService(db)
        session_service = SessionService(db)

        template = form_service.create_template(
            key="housing-confirmation", name="Housing Confirmation"
        )
        version = form_service.create_draft_version(
            form_template_id=template.id,
            source_language="de",
            supported_output_languages=["de", "en"],
        )
        form_service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="wohnungsgeber_name",
                field_type="string",
                required=True,
                position=1,
                translations=[
                    TranslationSchema(
                        language="de", label="Name und Anschrift des Wohnungsgebers"
                    ),
                    TranslationSchema(
                        language="en", label="Name and address of landlord"
                    ),
                ],
            ),
        )
        form_service.publish_version(version.id)

        session, raw_token = session_service.create_session(
            form_version_id=version.id,
            user_language="en",
            output_language="de",
        )
        session_service.start_session(session.public_id, raw_token)
        session_id = session.public_id
    finally:
        db.close()

    headers = {"X-Session-Token": raw_token}
    cf_res = client.get(
        f"/api/form-sessions/{session_id}/current-field", headers=headers
    )
    assert cf_res.status_code == 200
    cf_data = cf_res.json()
    assert "fieldExplanation" in cf_data
    assert cf_data["fieldExplanation"]["summary"]
    assert cf_data["fieldExplanation"]["whereToFind"]
    assert cf_data["fieldExplanation"]["example"]

    sum_res = client.get(f"/api/form-sessions/{session_id}/summary", headers=headers)
    assert sum_res.status_code == 200
    sum_data = sum_res.json()
    assert "submissionChecklist" in sum_data
    checklist_ids = [item["id"] for item in sum_data["submissionChecklist"]]
    assert "review_printed_values" in checklist_ids
    assert "landlord_counter_signature" in checklist_ids
    assert "identity_document_check" in checklist_ids
