"""Skipping an optional question.

The reported failure: the UI offered "Skip this question" but clicking it did
nothing. The frontend only re-fetched the current field, and the current-field
endpoint returns the *stored* position — which nothing had moved. Skipping is
now a real state change on the server.
"""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from app.main import app

# `session_setup` comes from tests/answers/conftest.py.

client = TestClient(app)


def _headers(token: str) -> dict[str, str]:
    return {"X-Session-Token": token}


def _skip(session_id: str, field_id: str, token: str) -> Any:
    return client.post(
        f"/api/form-sessions/{session_id}/fields/{field_id}/skip",
        headers=_headers(token),
    )


def test_optional_question_can_be_skipped(session_setup: dict[str, Any]) -> None:
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    optional_id = session_setup["field_ids"]["marital_status"]

    response = _skip(session_id, optional_id, token)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "skipped"


def test_skip_stores_no_value_rather_than_an_empty_string(
    session_setup: dict[str, Any],
) -> None:
    """An empty string would be validated, normalized and counted as invalid,
    and could not be told apart from an unreached question."""
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    optional_id = session_setup["field_ids"]["marital_status"]

    body = _skip(session_id, optional_id, token).json()

    assert body["originalAnswer"] in (None, "")
    assert body["normalizedValue"] is None
    assert body.get("outputValue") is None


def test_skip_runs_no_validation_and_needs_no_confirmation(
    session_setup: dict[str, Any],
) -> None:
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    optional_id = session_setup["field_ids"]["marital_status"]

    body = _skip(session_id, optional_id, token).json()

    assert body["validationStatus"] == "not_checked"
    assert body["requiresClarification"] is False
    assert body["confirmedByUser"] is False


def test_a_required_question_cannot_be_skipped(session_setup: dict[str, Any]) -> None:
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    required_id = session_setup["field_ids"]["first_name"]

    response = _skip(session_id, required_id, token)

    assert response.status_code == 422


def test_skip_advances_progress(session_setup: dict[str, Any]) -> None:
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    optional_id = session_setup["field_ids"]["marital_status"]

    before = client.get(
        f"/api/form-sessions/{session_id}/current-field", headers=_headers(token)
    ).json()["progress"]["answeredQuestions"]

    _skip(session_id, optional_id, token)

    after = client.get(
        f"/api/form-sessions/{session_id}/current-field", headers=_headers(token)
    ).json()["progress"]["answeredQuestions"]

    assert after == before + 1, "a deliberate skip is progress, not work left"


def test_skip_is_idempotent(session_setup: dict[str, Any]) -> None:
    """A double click must not produce two different outcomes."""
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    optional_id = session_setup["field_ids"]["marital_status"]

    first = _skip(session_id, optional_id, token).json()
    second = _skip(session_id, optional_id, token).json()

    assert first["answerId"] == second["answerId"]
    assert second["status"] == "skipped"


def test_skipped_state_survives_a_reload(session_setup: dict[str, Any]) -> None:
    """On resume a skipped question stays skipped rather than reappearing as
    unanswered."""
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    optional_id = session_setup["field_ids"]["marital_status"]

    _skip(session_id, optional_id, token)

    summary = client.get(
        f"/api/form-sessions/{session_id}/summary", headers=_headers(token)
    ).json()
    entry = next(f for f in summary["fields"] if f["fieldId"] == optional_id)

    assert entry["status"] == "skipped"
    assert entry["required"] is False


def test_a_skipped_question_can_still_be_answered_later(
    session_setup: dict[str, Any],
) -> None:
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    optional_id = session_setup["field_ids"]["marital_status"]

    _skip(session_id, optional_id, token)
    response = client.post(
        f"/api/form-sessions/{session_id}/answers",
        headers=_headers(token),
        json={"fieldId": optional_id, "originalAnswer": "single"},
    )

    assert response.status_code == 201
    assert response.json()["status"] != "skipped"


def test_skipping_an_unknown_field_is_rejected(session_setup: dict[str, Any]) -> None:
    session_id = session_setup["session_id"]
    token = session_setup["token"]

    response = _skip(session_id, "00000000-0000-0000-0000-000000000000", token)

    assert response.status_code == 422


def test_skip_requires_the_session_token(session_setup: dict[str, Any]) -> None:
    """Ownership is enforced here exactly as everywhere else."""
    session_id = session_setup["session_id"]
    optional_id = session_setup["field_ids"]["marital_status"]

    response = client.post(f"/api/form-sessions/{session_id}/fields/{optional_id}/skip")

    assert response.status_code in (401, 403)
