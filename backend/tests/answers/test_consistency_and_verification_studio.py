from __future__ import annotations

import uuid
from collections.abc import Generator
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.answers.consistency import evaluate_consistency_warnings
from app.answers.models import FormAnswer
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


def _field(
    field_id: str,
    key: str,
    field_type: str = "string",
    question_key: str | None = None,
) -> Any:
    return SimpleNamespace(
        id=field_id,
        key=key,
        field_type=field_type,
        question_key=question_key,
        translations=[],
    )


def _answer(
    value: Any,
    status: str = "confirmed",
    validation_status: str = "valid",
) -> Any:
    return SimpleNamespace(
        original_answer=str(value) if value is not None else None,
        normalized_value=value,
        output_value=str(value) if value is not None else None,
        status=status,
        validation_status=validation_status,
    )


def test_evaluate_consistency_warnings_catches_future_birth_and_move_in_before_birth() -> (
    None
):
    f_dob = _field("f1", "geburtsdatum", "date", "person.date_of_birth")
    f_move = _field("f2", "einzugsdatum", "date", "residence.move_in_date")
    version = SimpleNamespace(fields=[f_dob, f_move])

    # 1. Birth date in future across all 4 UI languages
    for lang in ("en", "de", "fr", "ar"):
        warnings = evaluate_consistency_warnings(
            version,
            {"f1": _answer("2099-05-01")},
            user_language=lang,
        )
        codes = [w["code"] for w in warnings]
        assert "birth_date_in_future" in codes
        assert warnings[0]["message"]

    # 2. Move-in date earlier than birth date
    warnings2 = evaluate_consistency_warnings(
        version,
        {"f1": _answer("1998-06-15"), "f2": _answer("1995-01-01")},
        user_language="en",
    )
    assert any(
        w["code"] == "move_in_before_birth_date"
        and set(w["field_keys"]) == {"geburtsdatum", "einzugsdatum"}
        for w in warnings2
    )


def test_evaluate_consistency_warnings_catches_end_before_start_and_postal_mismatch() -> (
    None
):
    f_start = _field("f1", "start_date", "date", "employment.start_date")
    f_end = _field("f2", "end_date", "date", "employment.end_date")
    f_country = _field("f3", "country", "country", "address.country")
    f_plz = _field("f4", "postal_code", "string", "address.postal_code")
    version = SimpleNamespace(fields=[f_start, f_end, f_country, f_plz])

    warnings = evaluate_consistency_warnings(
        version,
        {
            "f1": _answer("2025-10-01"),
            "f2": _answer("2025-05-01"),
            "f3": _answer("DE"),
            "f4": _answer("1234"),
        },
        user_language="de",
    )
    codes = {w["code"] for w in warnings}
    assert "end_date_before_start_date" in codes
    assert "postal_code_country_mismatch" in codes

    # Valid combination produces zero warnings
    clean = evaluate_consistency_warnings(
        version,
        {
            "f1": _answer("2025-01-01"),
            "f2": _answer("2025-12-31"),
            "f3": _answer("DE"),
            "f4": _answer("10115"),
        },
        user_language="de",
    )
    assert clean == []


def test_summary_endpoint_returns_source_labels_languages_and_consistency_warnings() -> (
    None
):
    db = SessionLocal()
    try:
        form_service = FormService(db)
        session_service = SessionService(db)

        template = form_service.create_template(
            key=f"studio-test-{uuid.uuid4().hex[:8]}",
            name="Verification Studio Form",
        )
        version = form_service.create_draft_version(
            form_template_id=template.id,
            source_language="de",
            supported_output_languages=["de", "en"],
        )
        f_dob = form_service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="geburtsdatum",
                field_type="date",
                required=True,
                position=1,
                question_key="person.date_of_birth",
                translations=[
                    TranslationSchema(language="de", label="Geburtsdatum"),
                    TranslationSchema(language="en", label="Date of birth"),
                ],
            ),
        )
        f_move = form_service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="einzugsdatum",
                field_type="date",
                required=True,
                position=2,
                question_key="residence.move_in_date",
                translations=[
                    TranslationSchema(language="de", label="Tag des Einzugs"),
                    TranslationSchema(language="en", label="Move-in date"),
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
        session_public_id = session.public_id

        db.add_all(
            [
                FormAnswer(
                    session_id=session.id,
                    field_id=f_dob.id,
                    original_answer="1999-09-10",
                    original_language="en",
                    normalized_value="1999-09-10",
                    output_value="1999-09-10",
                    status="confirmed",
                    validation_status="valid",
                    confirmed_by_user=True,
                ),
                FormAnswer(
                    session_id=session.id,
                    field_id=f_move.id,
                    original_answer="1995-01-01",
                    original_language="en",
                    normalized_value="1995-01-01",
                    output_value="1995-01-01",
                    status="confirmed",
                    validation_status="valid",
                    confirmed_by_user=True,
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    res = client.get(
        f"/api/form-sessions/{session_public_id}/summary",
        headers={"X-Session-Token": raw_token},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["sourceLanguage"] == "de"
    assert body["userLanguage"] == "en"
    assert body["outputLanguage"] == "de"
    assert isinstance(body["exportSupported"], bool)

    fields_by_key = {f["fieldKey"]: f for f in body["fields"]}
    assert fields_by_key["geburtsdatum"]["sourceLabel"] == "Geburtsdatum"
    assert fields_by_key["geburtsdatum"]["label"] == "Date of birth"
    assert fields_by_key["einzugsdatum"]["sourceLabel"] == "Tag des Einzugs"

    assert len(body["consistencyWarnings"]) == 1
    assert body["consistencyWarnings"][0]["code"] == "move_in_before_birth_date"
    assert set(body["consistencyWarnings"][0]["fieldKeys"]) == {
        "geburtsdatum",
        "einzugsdatum",
    }
