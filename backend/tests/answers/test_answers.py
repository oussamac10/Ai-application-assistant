import json
from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import app.ai.factory as ai_factory
from app.database.session import SessionLocal
from app.forms.schemas import (
    FieldCreate,
    OptionSchema,
    OptionTranslationSchema,
    TranslationSchema,
)
from app.forms.services import FormService
from app.main import app
from app.sessions.models import FormSession
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


@pytest.fixture
def session_setup() -> dict[str, Any]:
    db = SessionLocal()
    try:
        form_service = FormService(db)
        session_service = SessionService(db)

        # 1. Create template and version
        template = form_service.create_template(
            key="basic-registration", name="Basic Registration"
        )
        version = form_service.create_draft_version(
            form_template_id=template.id,
            source_language="en",
            supported_output_languages=["en", "de", "ar"],
        )

        # Add required field 1 (First Name)
        form_service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="first_name",
                field_type="person_name",
                required=True,
                position=1,
                translations=[
                    TranslationSchema(language="en", label="First Name"),
                    TranslationSchema(language="de", label="Vorname"),
                ],
            ),
        )

        # Add required field 2 (Income - Money)
        form_service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="monthly_income",
                field_type="money",
                required=True,
                position=2,
                translations=[TranslationSchema(language="en", label="Monthly Income")],
            ),
        )

        # Add optional field 3 (Marital Status - Choices)
        form_service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="marital_status",
                field_type="single_choice",
                required=False,
                position=3,
                translations=[TranslationSchema(language="en", label="Marital Status")],
                configuration={},
                options=[
                    OptionSchema(
                        value="single",
                        position=1,
                        translations=[
                            OptionTranslationSchema(language="en", label="Single"),
                            OptionTranslationSchema(language="de", label="Ledig"),
                            OptionTranslationSchema(language="ar", label="عازب"),
                        ],
                    ),
                    OptionSchema(
                        value="married",
                        position=2,
                        translations=[
                            OptionTranslationSchema(language="en", label="Married"),
                            OptionTranslationSchema(language="de", label="Verheiratet"),
                            OptionTranslationSchema(language="ar", label="متزوج"),
                        ],
                    ),
                ],
            ),
        )

        # Add optional field 4 (Request category - multi-select)
        form_service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="request_category",
                field_type="multiple_choice",
                required=False,
                position=4,
                translations=[
                    TranslationSchema(language="en", label="Request category")
                ],
                configuration={},
                options=[
                    OptionSchema(
                        value="Housing",
                        position=1,
                        translations=[
                            OptionTranslationSchema(language="en", label="Housing"),
                            OptionTranslationSchema(language="de", label="Wohnen"),
                            OptionTranslationSchema(language="ar", label="سكن"),
                        ],
                    ),
                    OptionSchema(
                        value="Education",
                        position=2,
                        translations=[
                            OptionTranslationSchema(language="en", label="Education"),
                            OptionTranslationSchema(language="de", label="Bildung"),
                            OptionTranslationSchema(language="ar", label="تعليم"),
                        ],
                    ),
                    OptionSchema(
                        value="Medical",
                        position=3,
                        translations=[
                            OptionTranslationSchema(language="en", label="Medical"),
                            OptionTranslationSchema(language="de", label="Medizinisch"),
                            OptionTranslationSchema(language="ar", label="طبي"),
                        ],
                    ),
                ],
            ),
        )

        # Publish version
        form_service.publish_version(version.id)

        # Create session
        session, token = session_service.create_session(
            form_version_id=version.id,
            user_language="en",
            output_language="de",
        )
        db.commit()

        # Start session to move to in_progress
        session_service.start_session(session.public_id, token)

        # Retrieve fields to get their IDs
        db.refresh(version)
        fields = {f.key: f.id for f in version.fields}

        session_id = session.public_id
        version_id = version.id
    finally:
        db.close()

    return {
        "session_id": session_id,
        "token": token,
        "version_id": version_id,
        "field_ids": fields,
    }


@pytest.fixture
def multi_choice_session_setup() -> dict[str, Any]:
    """A minimal session with a single required multiple_choice field, so
    it participates in the required-field position-scanning logic (unlike
    the optional `request_category` field in `session_setup`) — used to
    verify confirming a multi-select answer actually advances the session.
    """
    db = SessionLocal()
    try:
        form_service = FormService(db)
        session_service = SessionService(db)

        template = form_service.create_template(
            key="multi-choice-only", name="Multi Choice Only"
        )
        version = form_service.create_draft_version(
            form_template_id=template.id,
            source_language="en",
            supported_output_languages=["en"],
        )

        form_service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="request_category",
                field_type="multiple_choice",
                required=True,
                position=1,
                translations=[
                    TranslationSchema(language="en", label="Request category")
                ],
                configuration={},
                options=[
                    OptionSchema(
                        value="Housing",
                        position=1,
                        translations=[
                            OptionTranslationSchema(language="en", label="Housing")
                        ],
                    ),
                    OptionSchema(
                        value="Education",
                        position=2,
                        translations=[
                            OptionTranslationSchema(language="en", label="Education")
                        ],
                    ),
                    OptionSchema(
                        value="Medical",
                        position=3,
                        translations=[
                            OptionTranslationSchema(language="en", label="Medical")
                        ],
                    ),
                ],
            ),
        )
        form_service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="next_field",
                field_type="string",
                required=True,
                position=2,
                translations=[TranslationSchema(language="en", label="Next field")],
            ),
        )

        form_service.publish_version(version.id)

        session, token = session_service.create_session(
            form_version_id=version.id,
            user_language="en",
            output_language="en",
        )
        db.commit()
        session_service.start_session(session.public_id, token)

        db.refresh(version)
        fields = {f.key: f.id for f in version.fields}

        session_id = session.public_id
    finally:
        db.close()

    return {
        "session_id": session_id,
        "token": token,
        "field_ids": fields,
    }


def test_get_current_field(session_setup: dict[str, Any]) -> None:
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    first_name_id = session_setup["field_ids"]["first_name"]

    # 1. Fetch current field (should be first_name at position 1)
    response = client.get(
        f"/api/form-sessions/{session_id}/current-field",
        headers={"X-Session-Token": token},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["fieldId"] == first_name_id
    assert data["fieldType"] == "person_name"
    assert data["label"] == "First Name"
    assert data["progress"]["percentage"] == 0

    # Test language translation fallback
    # Create session with userLanguage = 'de'
    db = SessionLocal()
    session_service = SessionService(db)
    session_de, token_de = session_service.create_session(
        form_version_id=session_setup["version_id"],
        user_language="de",
        output_language="de",
    )
    db.commit()
    public_id_de = session_de.public_id
    db.close()

    response_de = client.get(
        f"/api/form-sessions/{public_id_de}/current-field",
        headers={"X-Session-Token": token_de},
    )
    assert response_de.status_code == 200
    assert response_de.json()["label"] == "Vorname"  # German translation


def test_submit_answer_person_name(session_setup: dict[str, Any]) -> None:
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    first_name_id = session_setup["field_ids"]["first_name"]

    # Submit valid name
    response = client.post(
        f"/api/form-sessions/{session_id}/answers",
        headers={"X-Session-Token": token},
        json={"fieldId": first_name_id, "originalAnswer": "Ahmed Benali"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "awaiting_confirmation"
    assert data["requiresClarification"] is False
    assert data["originalAnswer"] == "Ahmed Benali"
    assert data["normalizedValue"] == {"fullName": "Ahmed Benali"}
    assert data["outputValue"] == "Ahmed Benali"


def test_clarification_question_key_independent_of_user_language(
    session_setup: dict[str, Any],
) -> None:
    """Clarification messages must use user_language in both flows. The
    displayed text is resolved client-side (next-intl, keyed off the same
    session.user_language used everywhere else) from the stable
    question_key returned here — so that key's shape must be identical
    regardless of which user_language created the session, for both a
    Select-Manually session (this fixture's predefined form) and an
    Upload-Form one."""
    db = SessionLocal()
    session_service = SessionService(db)
    session_de, token_de = session_service.create_session(
        form_version_id=session_setup["version_id"],
        user_language="de",
        output_language="de",
    )
    db.commit()
    session_service.start_session(session_de.public_id, token_de)
    session_de_public_id = session_de.public_id
    income_id = session_setup["field_ids"]["monthly_income"]
    db.close()

    response = client.post(
        f"/api/form-sessions/{session_de_public_id}/answers",
        headers={"X-Session-Token": token_de},
        json={"fieldId": income_id, "originalAnswer": "1800"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "needs_clarification"
    # Same stable key as the English-user_language case below — the
    # frontend, not the backend, resolves this key into German text.
    assert data["clarification"]["questionKey"] == "money_missing_currency_and_period"


def test_submit_answer_money_clarification(session_setup: dict[str, Any]) -> None:
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    income_id = session_setup["field_ids"]["monthly_income"]

    # 1. Submit digits only (requires clarification)
    response = client.post(
        f"/api/form-sessions/{session_id}/answers",
        headers={"X-Session-Token": token},
        json={"fieldId": income_id, "originalAnswer": "1800"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "needs_clarification"
    assert data["requiresClarification"] is True
    assert data["clarification"]["missing"] == ["currency", "period"]
    assert data["clarification"]["questionKey"] == "money_missing_currency_and_period"
    answer_id = data["answerId"]

    # 2. Submit clarification values
    response_clarify = client.post(
        f"/api/form-sessions/{session_id}/answers/{answer_id}/clarify",
        headers={"X-Session-Token": token},
        json={"values": {"currency": "EUR", "period": "monthly"}},
    )
    assert response_clarify.status_code == 200
    data_clar = response_clarify.json()
    assert data_clar["status"] == "awaiting_confirmation"
    assert data_clar["requiresClarification"] is False
    assert data_clar["normalizedValue"] == {
        "amount": 1800.0,
        "currency": "EUR",
        "period": "monthly",
    }


def test_confirm_answer_and_progress(session_setup: dict[str, Any]) -> None:
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    first_name_id = session_setup["field_ids"]["first_name"]

    # Submit
    res_submit = client.post(
        f"/api/form-sessions/{session_id}/answers",
        headers={"X-Session-Token": token},
        json={"fieldId": first_name_id, "originalAnswer": "Ahmed Benali"},
    )
    answer_id = res_submit.json()["answerId"]

    # Try to confirm (should succeed because it's valid and awaiting_confirmation)
    res_confirm = client.post(
        f"/api/form-sessions/{session_id}/answers/{answer_id}/confirm",
        headers={"X-Session-Token": token},
    )
    assert res_confirm.status_code == 200
    assert res_confirm.json()["status"] == "confirmed"
    assert res_confirm.json()["confirmedByUser"] is True

    # Progress is measured over every question the user is asked, not only the
    # mandatory ones: with evidence-based requiredness (Phase 15) a form that
    # marks nothing mandatory would otherwise show "Question 1 of 0 (100%)".
    # The required counters keep their own meaning for completion checks.
    res_field = client.get(
        f"/api/form-sessions/{session_id}/current-field",
        headers={"X-Session-Token": token},
    )
    progress = res_field.json()["progress"]
    assert progress["confirmedRequiredFields"] == 1
    assert progress["totalRequiredFields"] == 2
    assert progress["answeredQuestions"] == 1
    assert progress["totalQuestions"] == 4
    assert progress["percentage"] == 25


def test_change_and_edit_answer(session_setup: dict[str, Any]) -> None:
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    first_name_id = session_setup["field_ids"]["first_name"]

    # 1. Submit & Confirm
    res_submit = client.post(
        f"/api/form-sessions/{session_id}/answers",
        headers={"X-Session-Token": token},
        json={"fieldId": first_name_id, "originalAnswer": "Ahmed Benali"},
    )
    answer_id = res_submit.json()["answerId"]
    client.post(
        f"/api/form-sessions/{session_id}/answers/{answer_id}/confirm",
        headers={"X-Session-Token": token},
    )

    # Verify progress is 50%
    res_sum1 = client.get(
        f"/api/form-sessions/{session_id}/summary",
        headers={"X-Session-Token": token},
    )
    assert res_sum1.json()["fields"][0]["confirmedByUser"] is True

    # 2. Edit answer (re-submitting via PUT)
    res_edit = client.put(
        f"/api/form-sessions/{session_id}/fields/{first_name_id}/answer",
        headers={"X-Session-Token": token},
        json={"originalAnswer": "Youssef Alaoui"},
    )
    assert res_edit.status_code == 200
    data_edit = res_edit.json()
    assert data_edit["status"] == "awaiting_confirmation"
    assert data_edit["confirmedByUser"] is False
    assert data_edit["originalAnswer"] == "Youssef Alaoui"

    # Summary should show confirmed = False
    res_sum2 = client.get(
        f"/api/form-sessions/{session_id}/summary",
        headers={"X-Session-Token": token},
    )
    assert res_sum2.json()["fields"][0]["confirmedByUser"] is False


def test_navigation_prev_field(session_setup: dict[str, Any]) -> None:
    session_id = session_setup["session_id"]
    token = session_setup["token"]

    # At position 1, previous field should fail with conflict 409
    res_prev = client.post(
        f"/api/form-sessions/{session_id}/previous-field",
        headers={"X-Session-Token": token},
    )
    assert res_prev.status_code == 409

    # Advance current field to position 2 by confirming position 1
    first_name_id = session_setup["field_ids"]["first_name"]
    res_sub = client.post(
        f"/api/form-sessions/{session_id}/answers",
        headers={"X-Session-Token": token},
        json={"fieldId": first_name_id, "originalAnswer": "Ahmed"},
    )
    client.post(
        f"/api/form-sessions/{session_id}/answers/{res_sub.json()['answerId']}/confirm",
        headers={"X-Session-Token": token},
    )

    # Stored position should be 2. Let's verify by retrieving current field.
    res_curr = client.get(
        f"/api/form-sessions/{session_id}/current-field",
        headers={"X-Session-Token": token},
    )
    assert res_curr.json()["position"] == 2

    # Now move previous-field (should go back to first_name at position 1)
    res_prev2 = client.post(
        f"/api/form-sessions/{session_id}/previous-field",
        headers={"X-Session-Token": token},
    )
    assert res_prev2.status_code == 200
    assert res_prev2.json()["fieldId"] == first_name_id
    assert res_prev2.json()["position"] == 1


def test_confirm_summary_workflow(session_setup: dict[str, Any]) -> None:
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    first_name_id = session_setup["field_ids"]["first_name"]
    income_id = session_setup["field_ids"]["monthly_income"]

    # Summary confirmation with missing answers should fail
    res_fail = client.post(
        f"/api/form-sessions/{session_id}/confirm-summary",
        headers={"X-Session-Token": token},
    )
    assert res_fail.status_code == 409

    # 1. Answer & confirm field 1 (First Name)
    res_sub1 = client.post(
        f"/api/form-sessions/{session_id}/answers",
        headers={"X-Session-Token": token},
        json={"fieldId": first_name_id, "originalAnswer": "Ahmed"},
    )
    client.post(
        f"/api/form-sessions/{session_id}/answers/{res_sub1.json()['answerId']}/confirm",
        headers={"X-Session-Token": token},
    )

    # 2. Answer & confirm field 2 (Money)
    res_sub2 = client.post(
        f"/api/form-sessions/{session_id}/answers",
        headers={"X-Session-Token": token},
        json={"fieldId": income_id, "originalAnswer": "1800 EUR monthly"},
    )
    client.post(
        f"/api/form-sessions/{session_id}/answers/{res_sub2.json()['answerId']}/confirm",
        headers={"X-Session-Token": token},
    )

    # 3. Confirm summary (now should succeed!)
    res_success = client.post(
        f"/api/form-sessions/{session_id}/confirm-summary",
        headers={"X-Session-Token": token},
    )
    assert res_success.status_code == 200
    assert res_success.json()["status"] == "ready_for_export"

    # Verify session is ready_for_export in database
    db = SessionLocal()
    sess = db.query(FormSession).filter_by(public_id=session_id).first()
    assert sess is not None
    assert sess.status == "ready_for_export"
    assert sess.completed_at is not None
    db.close()


def test_submit_multiple_choice_valid_array_is_awaiting_confirmation(
    session_setup: dict[str, Any],
) -> None:
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    category_id = session_setup["field_ids"]["request_category"]

    response = client.post(
        f"/api/form-sessions/{session_id}/answers",
        headers={"X-Session-Token": token},
        json={
            "fieldId": category_id,
            "originalAnswer": json.dumps(["Housing", "Education"]),
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "awaiting_confirmation"
    assert data["requiresClarification"] is False
    # Order and selected values are preserved exactly as submitted.
    assert data["normalizedValue"] == ["Housing", "Education"]


def test_submit_multiple_choice_rejects_option_not_in_configured_set(
    session_setup: dict[str, Any],
) -> None:
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    category_id = session_setup["field_ids"]["request_category"]

    response = client.post(
        f"/api/form-sessions/{session_id}/answers",
        headers={"X-Session-Token": token},
        json={
            "fieldId": category_id,
            "originalAnswer": json.dumps(["Housing", "NotAnOption"]),
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "draft"


def test_submit_multiple_choice_accepts_single_selected_option(
    session_setup: dict[str, Any],
) -> None:
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    category_id = session_setup["field_ids"]["request_category"]

    response = client.post(
        f"/api/form-sessions/{session_id}/answers",
        headers={"X-Session-Token": token},
        json={"fieldId": category_id, "originalAnswer": json.dumps(["Medical"])},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "awaiting_confirmation"
    assert data["normalizedValue"] == ["Medical"]


def test_multiple_choice_submission_never_calls_ai_provider(
    session_setup: dict[str, Any],
) -> None:
    """Choice fields are validated deterministically against their own
    configured options — the AI provider must never be consulted, so a
    dynamically detected field with no AI-visible option context (or any
    AI outage) can never block a valid submission."""
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    category_id = session_setup["field_ids"]["request_category"]

    class _ExplodingProvider:
        async def extract_value(self, request: Any) -> Any:
            raise AssertionError("AI provider must not be called for choice fields")

    original = ai_factory._provider
    ai_factory._provider = _ExplodingProvider()
    try:
        response = client.post(
            f"/api/form-sessions/{session_id}/answers",
            headers={"X-Session-Token": token},
            json={
                "fieldId": category_id,
                "originalAnswer": json.dumps(["Housing", "Education"]),
            },
        )
    finally:
        ai_factory._provider = original

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "awaiting_confirmation"
    assert data["requiresClarification"] is False
    assert data["clarification"] is None


def test_submit_single_choice_valid_option_is_awaiting_confirmation(
    session_setup: dict[str, Any],
) -> None:
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    marital_status_id = session_setup["field_ids"]["marital_status"]

    response = client.post(
        f"/api/form-sessions/{session_id}/answers",
        headers={"X-Session-Token": token},
        json={"fieldId": marital_status_id, "originalAnswer": "married"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "awaiting_confirmation"
    assert data["requiresClarification"] is False
    assert data["normalizedValue"] == "married"


def test_submit_single_choice_rejects_option_not_in_configured_set(
    session_setup: dict[str, Any],
) -> None:
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    marital_status_id = session_setup["field_ids"]["marital_status"]

    response = client.post(
        f"/api/form-sessions/{session_id}/answers",
        headers={"X-Session-Token": token},
        json={"fieldId": marital_status_id, "originalAnswer": "not_a_real_status"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "draft"
    assert data["requiresClarification"] is False


def test_multiple_choice_confirm_advances_to_next_question(
    multi_choice_session_setup: dict[str, Any],
) -> None:
    session_id = multi_choice_session_setup["session_id"]
    token = multi_choice_session_setup["token"]
    category_id = multi_choice_session_setup["field_ids"]["request_category"]
    next_field_id = multi_choice_session_setup["field_ids"]["next_field"]

    # The multiple_choice field is required and at position 1, so it must
    # be the current field before any answer is submitted.
    res_current_before = client.get(
        f"/api/form-sessions/{session_id}/current-field",
        headers={"X-Session-Token": token},
    )
    assert res_current_before.json()["fieldId"] == category_id

    res_submit = client.post(
        f"/api/form-sessions/{session_id}/answers",
        headers={"X-Session-Token": token},
        json={
            "fieldId": category_id,
            "originalAnswer": json.dumps(["Housing", "Education"]),
        },
    )
    assert res_submit.json()["status"] == "awaiting_confirmation"
    answer_id = res_submit.json()["answerId"]

    res_confirm = client.post(
        f"/api/form-sessions/{session_id}/answers/{answer_id}/confirm",
        headers={"X-Session-Token": token},
    )
    assert res_confirm.status_code == 200
    assert res_confirm.json()["status"] == "confirmed"

    # The session must now serve the next required field.
    res_current_after = client.get(
        f"/api/form-sessions/{session_id}/current-field",
        headers={"X-Session-Token": token},
    )
    assert res_current_after.json()["fieldId"] == next_field_id


def test_repeated_session_start_is_safe_and_idempotent(
    session_setup: dict[str, Any],
) -> None:
    session_id = session_setup["session_id"]
    token = session_setup["token"]

    # session_setup already started the session once; a duplicate /start
    # call (mirroring a duplicate frontend init effect) must succeed as a
    # no-op rather than surface a 409 that could break the guided-session UI.
    response = client.post(
        f"/api/form-sessions/{session_id}/start",
        headers={"X-Session-Token": token},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"

    # The session must still function normally afterwards.
    res_current = client.get(
        f"/api/form-sessions/{session_id}/current-field",
        headers={"X-Session-Token": token},
    )
    assert res_current.status_code == 200
