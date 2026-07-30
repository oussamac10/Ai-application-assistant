"""Confirming the summary: what blocks, what does not, and why.

The reported failure was a 409 on a question the user had left empty:

    POST /api/form-sessions/{id}/confirm-summary
    409  {"detail": "Field 'date_de_d_but_d_emploi' contains invalid value."}

Two separate defects, both in one line of `confirm_summary`:

    if ans:
        if ans.validation_status != "valid":  ->  "contains invalid value"

It ran on *any* answer record regardless of whether a value had ever been
submitted (a skip stores `not_checked` by design), and it ignored requiredness
entirely, so a question the document never marked mandatory could permanently
block the form.

Every test here is one cell of the requiredness x answer-state grid.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database.session import SessionLocal
from app.forms.schemas import FieldCreate, TranslationSchema
from app.forms.services import FormService
from app.main import app
from app.sessions.services import SessionService

client = TestClient(app)

DATE_KEY = "date_de_d_but_d_emploi"


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.commit()
        yield
    finally:
        db.close()


def _build_session(date_requiredness: str) -> dict[str, Any]:
    """A session whose employment-start-date field carries the requiredness
    under test, alongside one field of each other state."""
    db = SessionLocal()
    try:
        form_service = FormService(db)
        session_service = SessionService(db)

        template = form_service.create_template(
            key="french-employment", name="French employment form"
        )
        version = form_service.create_draft_version(
            form_template_id=template.id,
            source_language="fr",
            supported_output_languages=["fr", "en"],
        )

        form_service.add_field_to_draft(
            version.id,
            FieldCreate(
                key=DATE_KEY,
                field_type="date",
                requiredness=date_requiredness,
                position=1,
                translations=[
                    TranslationSchema(language="fr", label="Date de début d'emploi")
                ],
            ),
        )
        # A field the document said nothing about — the ordinary case for a
        # detected form, and the one that must never block.
        form_service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="nom_de_famille",
                field_type="string",
                requiredness="unknown",
                position=2,
                translations=[TranslationSchema(language="fr", label="Nom de famille")],
            ),
        )
        form_service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="deuxieme_prenom",
                field_type="string",
                requiredness="optional",
                position=3,
                translations=[
                    TranslationSchema(language="fr", label="Deuxième prénom")
                ],
            ),
        )
        form_service.publish_version(version.id)

        session, token = session_service.create_session(
            form_version_id=version.id,
            user_language="fr",
            output_language="fr",
        )
        db.commit()
        session_service.start_session(session.public_id, token)

        db.refresh(version)
        return {
            "session_id": session.public_id,
            "token": token,
            "field_ids": {f.key: f.id for f in version.fields},
        }
    finally:
        db.close()


def _headers(token: str) -> dict[str, str]:
    return {"X-Session-Token": token}


def _confirm(setup: dict[str, Any]) -> Any:
    return client.post(
        f"/api/form-sessions/{setup['session_id']}/confirm-summary",
        headers=_headers(setup["token"]),
    )


def _answer(setup: dict[str, Any], key: str, value: str) -> Any:
    return client.post(
        f"/api/form-sessions/{setup['session_id']}/answers",
        headers=_headers(setup["token"]),
        json={"fieldId": setup["field_ids"][key], "originalAnswer": value},
    )


def _confirm_answer(setup: dict[str, Any], answer_id: str) -> Any:
    return client.post(
        f"/api/form-sessions/{setup['session_id']}/answers/{answer_id}/confirm",
        headers=_headers(setup["token"]),
    )


def _skip(setup: dict[str, Any], key: str) -> Any:
    return client.post(
        f"/api/form-sessions/{setup['session_id']}"
        f"/fields/{setup['field_ids'][key]}/skip",
        headers=_headers(setup["token"]),
    )


def _answer_and_confirm(setup: dict[str, Any], key: str, value: str) -> None:
    response = _answer(setup, key, value)
    assert response.status_code == 201, response.text
    _confirm_answer(setup, response.json()["answerId"])


# ---------------------------------------------------------------------------
# The six reported cases, on the field that produced the bug report
# ---------------------------------------------------------------------------


def test_case_1_unknown_requiredness_unanswered_confirms() -> None:
    """The exact reported failure. Nothing marked the field mandatory, and the
    user left it empty; that is not an error."""
    setup = _build_session("unknown")

    response = _confirm(setup)

    assert response.status_code == 200
    assert response.json()["status"] == "ready_for_export"


def test_case_2_optional_unanswered_confirms() -> None:
    setup = _build_session("optional")

    assert _confirm(setup).status_code == 200


def test_case_3_optional_skipped_confirms() -> None:
    setup = _build_session("optional")
    assert _skip(setup, DATE_KEY).status_code == 200

    assert _confirm(setup).status_code == 200


def test_case_4_required_unanswered_reports_missing_required() -> None:
    setup = _build_session("required")

    response = _confirm(setup)

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "summary_not_confirmable"
    assert [p["field_key"] for p in body["missing_required_fields"]] == [DATE_KEY]
    assert body["invalid_answer_fields"] == []


def test_case_5_invalid_date_reports_invalid_date() -> None:
    setup = _build_session("optional")
    response = _answer(setup, DATE_KEY, "not a date")
    assert response.status_code == 201
    assert response.json()["validationStatus"] == "invalid"

    body = _confirm(setup).json()

    assert body["missing_required_fields"] == []
    assert body["invalid_answer_fields"] == [
        {"field_key": DATE_KEY, "reason": "invalid_date"}
    ]


def test_case_6_valid_date_confirms() -> None:
    setup = _build_session("required")
    _answer_and_confirm(setup, DATE_KEY, "2026-03-01")

    assert _confirm(setup).status_code == 200


# ---------------------------------------------------------------------------
# The requiredness x answer-state grid
# ---------------------------------------------------------------------------


def test_unknown_unanswered_does_not_block() -> None:
    setup = _build_session("optional")

    # `nom_de_famille` is `unknown` and untouched.
    assert _confirm(setup).status_code == 200


def test_skipped_unknown_field_does_not_block() -> None:
    setup = _build_session("optional")
    assert _skip(setup, "nom_de_famille").status_code == 200

    assert _confirm(setup).status_code == 200


def test_invalid_answer_on_an_unknown_field_still_blocks() -> None:
    """Requiredness governs *absence*, never correctness. A wrong date is
    wrong whether or not the form demanded one."""
    setup = _build_session("unknown")
    _answer(setup, DATE_KEY, "31/02/2026 maybe")

    response = _confirm(setup)

    assert response.status_code == 409
    assert response.json()["invalid_answer_fields"] == [
        {"field_key": DATE_KEY, "reason": "invalid_date"}
    ]


def test_answered_but_unconfirmed_required_field_blocks() -> None:
    setup = _build_session("required")
    assert _answer(setup, DATE_KEY, "2026-03-01").status_code == 201

    body = _confirm(setup).json()

    assert body["missing_required_fields"] == [
        {"field_key": DATE_KEY, "reason": "not_confirmed"}
    ]


def test_every_blocking_field_is_reported_at_once() -> None:
    """One field per round trip is the old behaviour: the first `raise` won."""
    setup = _build_session("required")
    _answer(setup, "nom_de_famille", "Dupont")  # answered, not confirmed, unknown

    body = _confirm(setup).json()

    assert [p["field_key"] for p in body["missing_required_fields"]] == [DATE_KEY]
    # `nom_de_famille` is unknown and valid: not blocking either way.
    assert body["invalid_answer_fields"] == []


# ---------------------------------------------------------------------------
# Values, blanks and privacy
# ---------------------------------------------------------------------------


def test_empty_submission_is_refused_rather_than_stored_as_skipped() -> None:
    """A blank is neither an answer nor a skip. Storing it would send an empty
    string into the date parser and the AI provider, which then report on a
    value that does not exist."""
    setup = _build_session("optional")

    response = _answer(setup, DATE_KEY, "   ")

    assert response.status_code == 422
    # And nothing was recorded as a skip behind the user's back.
    summary = client.get(
        f"/api/form-sessions/{setup['session_id']}/summary",
        headers=_headers(setup["token"]),
    ).json()
    row = next(f for f in summary["fields"] if f["fieldKey"] == DATE_KEY)
    assert row["answerState"] == "unreached"
    assert row["status"] != "skipped"


def test_structured_error_carries_keys_but_never_private_values() -> None:
    setup = _build_session("required")
    _answer(setup, "deuxieme_prenom", "Jean-Baptiste")
    _answer(setup, DATE_KEY, "pas une date du tout")

    body = _confirm(setup).json()
    serialized = str(body)

    assert DATE_KEY in serialized
    assert "Jean-Baptiste" not in serialized
    assert "pas une date du tout" not in serialized
    # Nor the human label, which can itself carry document content.
    assert "Date de début" not in serialized


# ---------------------------------------------------------------------------
# Summary, progress and resume
# ---------------------------------------------------------------------------


def test_summary_distinguishes_skipped_from_never_reached() -> None:
    setup = _build_session("optional")
    _skip(setup, DATE_KEY)

    summary = client.get(
        f"/api/form-sessions/{setup['session_id']}/summary",
        headers=_headers(setup["token"]),
    ).json()
    by_key = {f["fieldKey"]: f for f in summary["fields"]}

    assert by_key[DATE_KEY]["answerState"] == "skipped"
    assert by_key["nom_de_famille"]["answerState"] == "unreached"
    assert by_key["nom_de_famille"]["requiredness"] == "unknown"
    assert by_key["deuxieme_prenom"]["requiredness"] == "optional"


def test_resume_preserves_skipped_state() -> None:
    setup = _build_session("optional")
    _skip(setup, DATE_KEY)

    summary = client.get(
        f"/api/form-sessions/{setup['session_id']}/summary",
        headers=_headers(setup["token"]),
    ).json()
    row = next(f for f in summary["fields"] if f["fieldKey"] == DATE_KEY)

    assert row["status"] == "skipped"
    assert row["originalAnswer"] is None
    assert row["answerState"] == "skipped"


def test_progress_counts_skipped_questions_over_all_questions() -> None:
    setup = _build_session("unknown")
    _skip(setup, DATE_KEY)

    field = client.get(
        f"/api/form-sessions/{setup['session_id']}/current-field",
        headers=_headers(setup["token"]),
    ).json()

    # Three questions, none of them mandatory: the total must still be three,
    # not the required-field count of zero.
    assert field["progress"]["totalQuestions"] == 3
    assert field["progress"]["answeredQuestions"] == 1
    assert field["progress"]["totalRequiredFields"] == 0


def test_current_field_exposes_three_state_requiredness() -> None:
    setup = _build_session("required")

    field = client.get(
        f"/api/form-sessions/{setup['session_id']}/current-field",
        headers=_headers(setup["token"]),
    ).json()

    assert field["fieldKey"] == DATE_KEY
    assert field["requiredness"] == "required"
    assert field["required"] is True


def test_unknown_field_is_not_reported_as_optional() -> None:
    """`unknown` must survive the whole way to the client. Collapsing it into
    "optional" claims the document said something it did not."""
    setup = _build_session("unknown")

    field = client.get(
        f"/api/form-sessions/{setup['session_id']}/current-field",
        headers=_headers(setup["token"]),
    ).json()

    assert field["requiredness"] == "unknown"
    assert field["required"] is False


# ---------------------------------------------------------------------------
# Skipping across the three states
# ---------------------------------------------------------------------------


def test_skip_is_allowed_for_unknown_requiredness() -> None:
    setup = _build_session("unknown")

    assert _skip(setup, DATE_KEY).status_code == 200


def test_skip_is_refused_for_an_explicitly_required_field() -> None:
    setup = _build_session("required")

    assert _skip(setup, DATE_KEY).status_code == 422


# ---------------------------------------------------------------------------
# Reopening a question for editing
# ---------------------------------------------------------------------------


def test_a_skipped_question_can_be_reopened_and_answered() -> None:
    """Editing from the summary used to re-submit the stored answer, so a
    question with nothing in it could not be edited at all."""
    setup = _build_session("optional")
    _skip(setup, DATE_KEY)

    reopened = client.post(
        f"/api/form-sessions/{setup['session_id']}"
        f"/fields/{setup['field_ids'][DATE_KEY]}/reopen",
        headers=_headers(setup["token"]),
    )
    assert reopened.status_code == 200

    current = client.get(
        f"/api/form-sessions/{setup['session_id']}/current-field",
        headers=_headers(setup["token"]),
    ).json()
    assert current["fieldKey"] == DATE_KEY

    assert _answer(setup, DATE_KEY, "2026-03-01").status_code == 201


def test_reopening_a_confirmed_answer_keeps_its_value() -> None:
    setup = _build_session("optional")
    _answer_and_confirm(setup, DATE_KEY, "2026-03-01")

    client.post(
        f"/api/form-sessions/{setup['session_id']}"
        f"/fields/{setup['field_ids'][DATE_KEY]}/reopen",
        headers=_headers(setup["token"]),
    )

    summary = client.get(
        f"/api/form-sessions/{setup['session_id']}/summary",
        headers=_headers(setup["token"]),
    ).json()
    row = next(f for f in summary["fields"] if f["fieldKey"] == DATE_KEY)
    assert row["originalAnswer"] == "2026-03-01"
    assert row["status"] == "awaiting_confirmation"
