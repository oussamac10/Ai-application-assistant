"""Signatures: never electronically mandatory, never leaked, never guessed at.

Two product rules are under test.

**A required signature field does not mean a required digital signature.** When
a PDF marks its signature box required it is saying the printed document must
be signed before it counts — not that it must be signed inside this
application. Forcing an electronic signature would invent a requirement the
document never made and lock out anyone who cannot draw one on the device they
happen to be using.

**A signature is biometric personal data.** It never reaches a translator, an
AI provider or a log line, and a malformed payload is refused whole rather than
truncated — a partial signature must never render as though it were complete.
"""

from __future__ import annotations

from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.answers.signatures import (
    MAX_CANVAS_DIMENSION,
    MAX_POINTS_PER_STROKE,
    MAX_STROKES,
    PENDING_MANUAL_SIGNATURE,
    SIGNATURE_OPTIONAL,
    SIGNATURE_REQUIRED_BEFORE_SUBMISSION,
    SIGNATURE_UNKNOWN,
    SignatureValidationError,
    digital_signature_required,
    parse_signature,
    signature_requirement_from_field,
)
from app.database.session import SessionLocal
from app.forms.schemas import FieldCreate, TranslationSchema
from app.forms.services import FormService
from app.main import app
from app.sessions.services import SessionService

client = TestClient(app)

_VALID = {
    "strokes": [[[10.0, 10.0], [20.0, 25.0], [30.0, 12.0]]],
    "width": 400.0,
    "height": 200.0,
}


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.commit()
        yield
    finally:
        db.close()


def _session(signature_requiredness: str = "required") -> dict[str, Any]:
    db = SessionLocal()
    try:
        forms = FormService(db)
        sessions = SessionService(db)
        template = forms.create_template(key="sig-form", name="Signature form")
        version = forms.create_draft_version(
            form_template_id=template.id,
            source_language="fr",
            supported_output_languages=["fr"],
        )
        forms.add_field_to_draft(
            version.id,
            FieldCreate(
                key="nom",
                field_type="string",
                requiredness="required",
                position=1,
                translations=[TranslationSchema(language="fr", label="Nom")],
            ),
        )
        forms.add_field_to_draft(
            version.id,
            FieldCreate(
                key="signature",
                field_type="signature",
                requiredness=signature_requiredness,
                position=2,
                translations=[TranslationSchema(language="fr", label="Signature")],
            ),
        )
        forms.publish_version(version.id)
        session, token = sessions.create_session(
            form_version_id=version.id, user_language="fr", output_language="fr"
        )
        db.commit()
        sessions.start_session(session.public_id, token)
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


def _sign(setup: dict[str, Any], payload: Any) -> Any:
    return client.post(
        f"/api/form-sessions/{setup['session_id']}"
        f"/fields/{setup['field_ids']['signature']}/signature",
        headers=_headers(setup["token"]),
        json=payload,
    )


def _defer(setup: dict[str, Any]) -> Any:
    return client.post(
        f"/api/form-sessions/{setup['session_id']}"
        f"/fields/{setup['field_ids']['signature']}/sign-after-printing",
        headers=_headers(setup["token"]),
    )


def _answer_and_confirm(setup: dict[str, Any], key: str, value: str) -> None:
    response = client.post(
        f"/api/form-sessions/{setup['session_id']}/answers",
        headers=_headers(setup["token"]),
        json={"fieldId": setup["field_ids"][key], "originalAnswer": value},
    )
    assert response.status_code == 201, response.text
    client.post(
        f"/api/form-sessions/{setup['session_id']}"
        f"/answers/{response.json()['answerId']}/confirm",
        headers=_headers(setup["token"]),
    )


def _confirm_summary(setup: dict[str, Any]) -> Any:
    return client.post(
        f"/api/form-sessions/{setup['session_id']}/confirm-summary",
        headers=_headers(setup["token"]),
    )


def _summary_row(setup: dict[str, Any], key: str) -> dict[str, Any]:
    body = client.get(
        f"/api/form-sessions/{setup['session_id']}/summary",
        headers=_headers(setup["token"]),
    ).json()
    return next(f for f in body["fields"] if f["fieldKey"] == key)


# ---------------------------------------------------------------------------
# Payload validation
# ---------------------------------------------------------------------------


def test_a_well_formed_signature_is_accepted() -> None:
    signature = parse_signature(_VALID)

    assert len(signature.strokes) == 1
    assert signature.point_count == 3
    # Stroke order is preserved — it is what makes the rendered signature look
    # like the one that was drawn.
    assert signature.strokes[0][0] == (10.0, 10.0)
    assert signature.strokes[0][-1] == (30.0, 12.0)


@pytest.mark.parametrize(
    "payload,reason",
    [
        ("not an object", "a string is not a payload"),
        ({"width": 400, "height": 200}, "no strokes"),
        ({"strokes": [], "width": 400, "height": 200}, "empty stroke list"),
        ({"strokes": [[]], "width": 400, "height": 200}, "empty stroke"),
        ({"strokes": [[[1, 2]]], "width": 0, "height": 200}, "zero width"),
        (
            {"strokes": [[[1, 2]]], "width": MAX_CANVAS_DIMENSION + 1, "height": 200},
            "canvas too large",
        ),
        ({"strokes": [[[1, 2, 3]]], "width": 400, "height": 200}, "not an [x, y] pair"),
        ({"strokes": [[["a", "b"]]], "width": 400, "height": 200}, "non-numeric"),
        ({"strokes": [[[9999, 2]]], "width": 400, "height": 200}, "outside the canvas"),
        (
            {"strokes": [[[float("nan"), 2]]], "width": 400, "height": 200},
            "NaN survives an isinstance check and would reach the renderer",
        ),
        (
            {"strokes": [[[float("inf"), 2]]], "width": 400, "height": 200},
            "infinity likewise",
        ),
    ],
)
def test_malformed_payloads_are_rejected(payload: Any, reason: str) -> None:
    with pytest.raises(SignatureValidationError):
        parse_signature(payload)


def test_an_oversized_payload_is_rejected() -> None:
    """Bounds exist so no request can store bulk data or exhaust memory."""
    too_many_strokes = {
        "strokes": [[[1.0, 1.0], [2.0, 2.0]] for _ in range(MAX_STROKES + 1)],
        "width": 400.0,
        "height": 200.0,
    }
    with pytest.raises(SignatureValidationError):
        parse_signature(too_many_strokes)

    too_many_points = {
        "strokes": [[[1.0, 1.0]] * (MAX_POINTS_PER_STROKE + 1)],
        "width": 400.0,
        "height": 200.0,
    }
    with pytest.raises(SignatureValidationError):
        parse_signature(too_many_points)


def test_a_payload_cannot_carry_markup() -> None:
    """The format holds numbers only, so an SVG or script payload has nowhere
    to live — it fails as a type error rather than needing to be sanitised."""
    with pytest.raises(SignatureValidationError):
        parse_signature(
            {
                "strokes": [[["<script>alert(1)</script>", 0]]],
                "width": 400.0,
                "height": 200.0,
            }
        )


def test_a_rejection_never_echoes_the_payload() -> None:
    with pytest.raises(SignatureValidationError) as exc:
        parse_signature(
            {"strokes": [[[99999.0, 42.0]]], "width": 400.0, "height": 200.0}
        )

    assert "99999" not in str(exc.value)


# ---------------------------------------------------------------------------
# Electronic signing is never mandatory
# ---------------------------------------------------------------------------


def test_digital_signing_is_never_required() -> None:
    assert digital_signature_required() is False


def test_the_document_requirement_is_reported_separately() -> None:
    """What the document said and how the user may satisfy it are different
    questions, and only the first varies."""

    class _Field:
        def __init__(self, state: str) -> None:
            self.requiredness = state
            self.required = state == "required"

    assert (
        signature_requirement_from_field(_Field("required"))
        == SIGNATURE_REQUIRED_BEFORE_SUBMISSION
    )
    assert signature_requirement_from_field(_Field("optional")) == SIGNATURE_OPTIONAL
    assert signature_requirement_from_field(_Field("unknown")) == SIGNATURE_UNKNOWN


def test_a_required_signature_field_reports_that_digital_signing_is_optional() -> None:
    setup = _session("required")

    field = client.get(
        f"/api/form-sessions/{setup['session_id']}/current-field",
        headers=_headers(setup["token"]),
    ).json()
    _answer_and_confirm(setup, "nom", "Dupont")
    field = client.get(
        f"/api/form-sessions/{setup['session_id']}/current-field",
        headers=_headers(setup["token"]),
    ).json()

    assert field["fieldKey"] == "signature"
    assert field["signatureRequirement"] == SIGNATURE_REQUIRED_BEFORE_SUBMISSION
    assert field["digitalSignatureRequired"] is False


# ---------------------------------------------------------------------------
# Sign after printing
# ---------------------------------------------------------------------------


def test_sign_after_printing_is_accepted_for_a_required_signature() -> None:
    """The whole point: the document demands a signature, and the user may
    still choose to provide it on paper."""
    setup = _session("required")

    response = _defer(setup)

    assert response.status_code == 200
    assert response.json()["status"] == PENDING_MANUAL_SIGNATURE
    assert response.json()["originalAnswer"] is None


def test_sign_after_printing_does_not_block_confirmation() -> None:
    setup = _session("required")
    _answer_and_confirm(setup, "nom", "Dupont")
    _defer(setup)

    assert _confirm_summary(setup).status_code == 200


def test_sign_after_printing_is_not_a_skip() -> None:
    """It is a decision about how the form will be completed, and the summary
    must be able to say "Will be signed after printing" rather than
    "Skipped"."""
    setup = _session("required")
    _defer(setup)

    row = _summary_row(setup, "signature")

    assert row["answerState"] == PENDING_MANUAL_SIGNATURE
    assert row["status"] == PENDING_MANUAL_SIGNATURE
    assert row["status"] != "skipped"


def test_a_required_signature_left_untouched_still_blocks() -> None:
    """Deferring is a decision; ignoring the question is not."""
    setup = _session("required")
    _answer_and_confirm(setup, "nom", "Dupont")

    response = _confirm_summary(setup)

    assert response.status_code == 409
    assert [p["field_key"] for p in response.json()["missing_required_fields"]] == [
        "signature"
    ]


def test_a_manual_signature_survives_resume() -> None:
    setup = _session("optional")
    _defer(setup)

    assert _summary_row(setup, "signature")["status"] == PENDING_MANUAL_SIGNATURE


def test_a_deferred_signature_can_later_be_signed_digitally() -> None:
    """The user must be able to change their mind."""
    setup = _session("required")
    _defer(setup)

    response = _sign(setup, _VALID)

    assert response.status_code == 200
    assert response.json()["status"] == "awaiting_confirmation"
    assert _summary_row(setup, "signature")["status"] != PENDING_MANUAL_SIGNATURE


# ---------------------------------------------------------------------------
# Capture through the API
# ---------------------------------------------------------------------------


def test_a_drawn_signature_is_stored_as_vectors() -> None:
    setup = _session("required")

    response = _sign(setup, _VALID)

    assert response.status_code == 200
    stored = response.json()["normalizedValue"]
    assert stored["strokes"] == [[[10.0, 10.0], [20.0, 25.0], [30.0, 12.0]]]
    # Never as text: putting it in `original_answer` would feed it to every
    # code path that handles text, including translation.
    assert response.json()["originalAnswer"] is None


def test_a_malformed_signature_is_refused_by_the_api() -> None:
    setup = _session("required")

    response = _sign(
        setup, {"strokes": [[[9999.0, 1.0]]], "width": 10.0, "height": 10.0}
    )

    assert response.status_code == 422


def test_a_signature_cannot_be_posted_to_a_non_signature_field() -> None:
    setup = _session("required")

    response = client.post(
        f"/api/form-sessions/{setup['session_id']}"
        f"/fields/{setup['field_ids']['nom']}/signature",
        headers=_headers(setup["token"]),
        json=_VALID,
    )

    assert response.status_code == 422


def test_signature_capture_is_not_logged(caplog: pytest.LogCaptureFixture) -> None:
    """Counts only. A signature is biometric personal data."""
    setup = _session("required")

    with caplog.at_level("INFO"):
        _sign(setup, _VALID)

    logged = "\n".join(record.getMessage() for record in caplog.records)
    assert "10.0" not in logged or "strokes=1" in logged
    assert "[[10.0, 10.0]" not in logged
    assert "strokes=1" in logged
    assert "points=3" in logged
