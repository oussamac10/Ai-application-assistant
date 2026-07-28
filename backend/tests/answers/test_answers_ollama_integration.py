"""Integration tests for the real answer-submission workflow with
AI_PROVIDER=ollama — the Ollama HTTP call itself is mocked (no live Ollama
required), but everything else (routing, AnswerService, normalization,
validation, status transitions) runs for real.

These reproduce the originally reported failure: a valid Ollama response
(final answer entirely in `response`, thinking disabled) must let the
answer proceed to `awaiting_confirmation`, not fail with a generic
"temporarily unavailable" error.
"""

from __future__ import annotations

import json
from collections.abc import Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

import app.ai.factory as ai_factory
from app.ai.ollama_provider import OllamaAIProvider
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


@pytest.fixture
def ollama_provider() -> Generator[OllamaAIProvider, None, None]:
    """Installs a real OllamaAIProvider as the process-level singleton for
    the duration of the test, restoring whatever was there before —
    mirroring how AI_PROVIDER=ollama wires it up via app.ai.factory, but
    without needing a live Ollama instance."""
    original = ai_factory._provider
    provider = OllamaAIProvider(
        base_url="http://ollama.invalid:11434",
        model="test-model",
        timeout_seconds=5,
        max_retries=0,
    )
    ai_factory._provider = provider
    yield provider
    ai_factory._provider = original


@pytest.fixture
def session_setup() -> dict[str, Any]:
    db = SessionLocal()
    try:
        form_service = FormService(db)
        session_service = SessionService(db)

        template = form_service.create_template(
            key="ollama-integration", name="Ollama Integration"
        )
        version = form_service.create_draft_version(
            form_template_id=template.id,
            source_language="en",
            supported_output_languages=["en"],
        )
        form_service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="full_name",
                field_type="person_name",
                required=True,
                position=1,
                translations=[TranslationSchema(language="en", label="Full name")],
            ),
        )
        form_service.add_field_to_draft(
            version.id,
            FieldCreate(
                key="bio",
                field_type="multiline_text",
                required=False,
                position=2,
                translations=[
                    TranslationSchema(language="en", label="Situation"),
                    TranslationSchema(language="fr", label="Situation"),
                ],
            ),
        )
        form_service.publish_version(version.id)

        session, token = session_service.create_session(
            form_version_id=version.id,
            user_language="fr",
            output_language="en",
        )
        db.commit()
        session_service.start_session(session.public_id, token)

        db.refresh(version)
        field_ids = {f.key: f.id for f in version.fields}
        session_id = session.public_id
    finally:
        db.close()

    return {"session_id": session_id, "token": token, "field_ids": field_ids}


def _ollama_http_response(
    body: dict[str, Any], thinking: str | None = None
) -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    payload: dict[str, Any] = {"response": json.dumps(body), "done": True}
    if thinking is not None:
        payload["thinking"] = thinking
    resp.json.return_value = payload
    return resp


def test_valid_ollama_response_reaches_awaiting_confirmation(
    ollama_provider: OllamaAIProvider, session_setup: dict[str, Any]
) -> None:
    """The originally reported failure: submitting "oussama" for a Full
    name field with AI_PROVIDER=ollama must succeed end-to-end, not show
    the generic AI-unavailable error."""
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    field_id = session_setup["field_ids"]["full_name"]

    ollama_body = {
        "normalizedValue": {
            "fullName": "oussama",
            "givenName": "oussama",
            "familyName": "",
        },
        "outputValue": "oussama",
        "requiresClarification": False,
        "uncertainties": [],
    }

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        return_value=_ollama_http_response(ollama_body),
    ):
        response = client.post(
            f"/api/form-sessions/{session_id}/answers",
            headers={"X-Session-Token": token},
            json={"fieldId": field_id, "originalAnswer": "oussama"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "awaiting_confirmation"
    assert data["normalizedValue"] == ollama_body["normalizedValue"]
    # The original answer is preserved verbatim regardless of normalization.
    assert data["originalAnswer"] == "oussama"


def test_ollama_response_with_thinking_field_still_succeeds(
    ollama_provider: OllamaAIProvider, session_setup: dict[str, Any]
) -> None:
    """A response carrying both `response` and `thinking` must be accepted
    using `response` only — this is the exact shape a reasoning model like
    qwen3 returns when it does emit a clean final answer."""
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    field_id = session_setup["field_ids"]["full_name"]

    ollama_body = {
        "normalizedValue": {
            "fullName": "oussama",
            "givenName": "oussama",
            "familyName": "",
        },
        "outputValue": "oussama",
        "requiresClarification": False,
        "uncertainties": [],
    }

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        return_value=_ollama_http_response(
            ollama_body, thinking="Okay, the user's name is oussama..."
        ),
    ):
        response = client.post(
            f"/api/form-sessions/{session_id}/answers",
            headers={"X-Session-Token": token},
            json={"fieldId": field_id, "originalAnswer": "oussama"},
        )

    assert response.status_code == 201
    assert response.json()["status"] == "awaiting_confirmation"
    # No trace of the chain-of-thought content anywhere in the API response.
    assert "thinking" not in response.text
    assert "Let me think" not in response.text


def test_ollama_timeout_preserves_original_answer_and_returns_safe_error(
    ollama_provider: OllamaAIProvider, session_setup: dict[str, Any]
) -> None:
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    field_id = session_setup["field_ids"]["full_name"]

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=httpx.ReadTimeout("timed out", request=MagicMock()),
    ):
        response = client.post(
            f"/api/form-sessions/{session_id}/answers",
            headers={"X-Session-Token": token},
            json={"fieldId": field_id, "originalAnswer": "oussama"},
        )

    assert response.status_code == 504
    # No internal detail (URLs, stack traces, model name) leaks to the client.
    assert "ollama.invalid" not in response.text.lower()
    assert "traceback" not in response.text.lower()

    # No answer was persisted — nothing to roll back, original input is
    # simply never overwritten, matching "original answer preserved".
    res_current = client.get(
        f"/api/form-sessions/{session_id}/current-field",
        headers={"X-Session-Token": token},
    )
    assert res_current.json()["currentAnswerStatus"] is None


def test_ollama_connection_failure_returns_safe_error(
    ollama_provider: OllamaAIProvider, session_setup: dict[str, Any]
) -> None:
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    field_id = session_setup["field_ids"]["full_name"]

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=httpx.ConnectError("refused"),
    ):
        response = client.post(
            f"/api/form-sessions/{session_id}/answers",
            headers={"X-Session-Token": token},
            json={"fieldId": field_id, "originalAnswer": "oussama"},
        )

    assert response.status_code == 503
    assert "ollama.invalid" not in response.text.lower()


def test_ollama_empty_response_falls_back_safely_never_500(
    ollama_provider: OllamaAIProvider, session_setup: dict[str, Any]
) -> None:
    """Reproduces the exact real-world failure mode: Ollama answers with
    done=True but an empty `response` (the model's answer was absorbed
    into `thinking`), and the bounded repair retry also comes back empty.

    A response *was* received (this is not a connectivity failure), so the
    answer submission must not hard-fail: it falls back to the original
    answer, deterministically normalized, never a 500 and never any
    "thinking"/raw-model content in the response body."""
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    field_id = session_setup["field_ids"]["full_name"]

    empty_resp = MagicMock()
    empty_resp.status_code = 200
    empty_resp.raise_for_status = MagicMock()
    empty_resp.json.return_value = {
        "response": "",
        "thinking": '{"normalizedValue": {"fullName": "oussama"}}',
        "done": True,
        "done_reason": "stop",
    }

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        return_value=empty_resp,
    ):
        response = client.post(
            f"/api/form-sessions/{session_id}/answers",
            headers={"X-Session-Token": token},
            json={"fieldId": field_id, "originalAnswer": "oussama"},
        )

    assert response.status_code == 201
    assert "thinking" not in response.text
    data = response.json()
    assert data["requiresClarification"] is False


# ---------------------------------------------------------------------------
# Reasoning-as-object-key bug (French multiline_text -> English)
# ---------------------------------------------------------------------------
#
# Reproduces the exact reported bug: user_language=fr, output_language=en,
# field_type=multiline_text, answer="Je suis marié". Ollama returns
# syntactically valid JSON with the correct top-level keys, but nests its
# reasoning as the *value* of normalizedValue instead of a plain string:
#   {"normalizedValue": {"The user's answer 'Je suis marié' translates to
#   'I am married' in French, but the field is a multiline_text field...":
#   "marié"}, "outputValue": null, "requiresClarification": false,
#   "uncertainties": []}
# Before the fix, normalize_value()'s multiline_text branch (`str(raw_val)`)
# stringified that nested dict verbatim, which is exactly the malformed
# value the UI showed.


def test_reasoning_as_normalized_value_object_key_is_rejected_and_repaired(
    ollama_provider: OllamaAIProvider, session_setup: dict[str, Any]
) -> None:
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    field_id = session_setup["field_ids"]["bio"]

    bad_resp = MagicMock()
    bad_resp.status_code = 200
    bad_resp.raise_for_status = MagicMock()
    bad_resp.json.return_value = {
        "response": json.dumps(
            {
                "normalizedValue": {
                    "The user's answer 'Je suis marié' translates to 'I am "
                    "married' in French, but the field is a multiline_text "
                    "field...": "marié"
                },
                "outputValue": None,
                "requiresClarification": False,
                "uncertainties": [],
            }
        ),
        "done": True,
    }
    good_resp = _ollama_http_response(
        {
            "normalizedValue": "I am married",
            "outputValue": "I am married",
            "requiresClarification": False,
            "uncertainties": [],
        }
    )

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=[bad_resp, good_resp],
    ) as mock_post:
        response = client.post(
            f"/api/form-sessions/{session_id}/answers",
            headers={"X-Session-Token": token},
            json={"fieldId": field_id, "originalAnswer": "Je suis marié"},
        )

    assert mock_post.call_count == 2
    assert response.status_code == 201
    data = response.json()
    assert data["normalizedValue"] == "I am married"
    assert data["outputValue"] == "I am married"
    assert data["requiresClarification"] is False
    assert data["originalAnswer"] == "Je suis marié"
    assert data["status"] == "awaiting_confirmation"
    # The malformed reasoning-as-key content must never reach the client.
    assert "translates to" not in response.text
    assert "multiline_text field" not in response.text


def test_reasoning_as_key_still_malformed_after_repair_falls_back_to_original_answer(
    ollama_provider: OllamaAIProvider, session_setup: dict[str, Any]
) -> None:
    """If the repair retry *also* nests reasoning under normalizedValue,
    the answer must fall back to the original text — never a raw dict, and
    never a hard failure since a response was received both times."""
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    field_id = session_setup["field_ids"]["bio"]

    def _bad_resp() -> MagicMock:
        resp = MagicMock()
        resp.status_code = 200
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "response": json.dumps(
                {
                    "normalizedValue": {
                        "The user's answer 'Je suis marié' translates to "
                        "'I am married'...": "marié"
                    },
                    "outputValue": None,
                    "requiresClarification": False,
                    "uncertainties": [],
                }
            ),
            "done": True,
        }
        return resp

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=[_bad_resp(), _bad_resp()],
    ) as mock_post:
        response = client.post(
            f"/api/form-sessions/{session_id}/answers",
            headers={"X-Session-Token": token},
            json={"fieldId": field_id, "originalAnswer": "Je suis marié"},
        )

    assert mock_post.call_count == 2
    assert response.status_code == 201
    data = response.json()
    assert data["normalizedValue"] == "Je suis marié"
    assert data["requiresClarification"] is False
    assert data["originalAnswer"] == "Je suis marié"
    assert "translates to" not in response.text


def test_unexpected_top_level_key_rejected_and_repaired(
    ollama_provider: OllamaAIProvider, session_setup: dict[str, Any]
) -> None:
    """A response with an unexpected extra top-level key (alongside
    otherwise-correct keys) must be rejected by strict schema validation,
    not silently accepted with the extra key ignored."""
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    field_id = session_setup["field_ids"]["bio"]

    bad_resp = MagicMock()
    bad_resp.status_code = 200
    bad_resp.raise_for_status = MagicMock()
    bad_resp.json.return_value = {
        "response": json.dumps(
            {
                "normalizedValue": "I am married",
                "outputValue": "I am married",
                "requiresClarification": False,
                "uncertainties": [],
                "reasoning": "The user's answer translates to 'I am married'.",
            }
        ),
        "done": True,
    }
    good_resp = _ollama_http_response(
        {
            "normalizedValue": "I am married",
            "outputValue": "I am married",
            "requiresClarification": False,
            "uncertainties": [],
        }
    )

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=[bad_resp, good_resp],
    ) as mock_post:
        response = client.post(
            f"/api/form-sessions/{session_id}/answers",
            headers={"X-Session-Token": token},
            json={"fieldId": field_id, "originalAnswer": "Je suis marié"},
        )

    assert mock_post.call_count == 2
    assert response.status_code == 201
    assert response.json()["normalizedValue"] == "I am married"


def test_multiline_french_to_english_translation_no_clarification(
    ollama_provider: OllamaAIProvider, session_setup: dict[str, Any]
) -> None:
    """The exact expected-behavior example from the bug report."""
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    field_id = session_setup["field_ids"]["bio"]

    ollama_body = {
        "normalizedValue": "I am married",
        "outputValue": "I am married",
        "requiresClarification": False,
        "uncertainties": [],
    }

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        return_value=_ollama_http_response(ollama_body),
    ):
        response = client.post(
            f"/api/form-sessions/{session_id}/answers",
            headers={"X-Session-Token": token},
            json={"fieldId": field_id, "originalAnswer": "Je suis marié"},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["originalAnswer"] == "Je suis marié"
    assert data["normalizedValue"] == "I am married"
    assert data["outputValue"] == "I am married"
    assert data["requiresClarification"] is False
    assert data["status"] == "awaiting_confirmation"
    assert isinstance(data["normalizedValue"], str)


def test_multiline_text_non_empty_free_form_answer_never_requires_clarification(
    ollama_provider: OllamaAIProvider, session_setup: dict[str, Any]
) -> None:
    """A non-empty multiline_text answer must never be routed to
    clarification merely for being free-form, even if the model itself
    (incorrectly) suggests otherwise for a value that deterministically
    validates fine."""
    session_id = session_setup["session_id"]
    token = session_setup["token"]
    field_id = session_setup["field_ids"]["bio"]

    ollama_body = {
        "normalizedValue": "  I am married and live in Paris.  ",
        "outputValue": "I am married and live in Paris.",
        "requiresClarification": False,
        "uncertainties": [],
    }

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        return_value=_ollama_http_response(ollama_body),
    ):
        response = client.post(
            f"/api/form-sessions/{session_id}/answers",
            headers={"X-Session-Token": token},
            json={
                "fieldId": field_id,
                "originalAnswer": "Je suis marié et je vis à Paris.",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "awaiting_confirmation"
    assert data["requiresClarification"] is False
    # Whitespace is cleaned by deterministic normalization.
    assert data["normalizedValue"] == "I am married and live in Paris."
