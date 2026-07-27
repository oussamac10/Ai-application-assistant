"""Regression tests for the Phase 12 authorization gap: field-detection,
OCR, and document access must work under both the anonymous ownership-token
model and the authenticated dual-ownership model, and claiming a session
must transfer ownership of its linked source document (and therefore its
field-detection/OCR results) to the account — not leave them permanently
anonymous-only.
"""

from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import text

from app.core.config import settings
from app.database.session import SessionLocal
from app.main import app

REGISTER_PASSWORD = "correct-horse-battery"

# Module-level clients (not `with TestClient(app) as c`) to avoid
# destabilizing the shared SQLAlchemy connection pool — see the Phase 12
# session-handoff notes on this exact failure mode.
client = TestClient(app)
other_client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    client.cookies.clear()
    other_client.cookies.clear()
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE source_documents CASCADE"))
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.execute(text("TRUNCATE TABLE form_sessions CASCADE"))
        db.execute(text("TRUNCATE TABLE users CASCADE"))
        db.commit()
        yield
    except Exception:
        db.rollback()
    finally:
        db.close()
        client.cookies.clear()
        other_client.cookies.clear()


@pytest.fixture(autouse=True)
def use_mock_provider() -> Generator[None, None, None]:
    original = settings.FIELD_DETECTION_PROVIDER
    settings.FIELD_DETECTION_PROVIDER = "mock"
    yield
    settings.FIELD_DETECTION_PROVIDER = original


def _create_digital_pdf(filepath: str) -> None:
    c = canvas.Canvas(filepath, pagesize=letter)
    c.drawString(100, 700, "Just some unmatched content")
    c.showPage()
    c.save()


def _upload_digital_document(
    c: TestClient, tmp_path: Path, name: str = "digital.pdf"
) -> tuple[str, str]:
    pdf_path = tmp_path / name
    _create_digital_pdf(str(pdf_path))
    with open(pdf_path, "rb") as f:
        response = c.post(
            "/api/source-documents",
            data={"language": "en", "outputLanguage": "en", "privacyAccepted": "true"},
            files={"file": (name, f, "application/pdf")},
        )
    assert response.status_code == 201
    data = response.json()
    assert data["analysis"]["nextStep"] == "dynamic_field_detection"
    return data["documentId"], data["ownershipToken"]


def _register(c: TestClient, email: str) -> None:
    response = c.post(
        "/api/auth/register",
        json={
            "email": email,
            "password": REGISTER_PASSWORD,
            "passwordConfirmation": REGISTER_PASSWORD,
        },
    )
    assert response.status_code == 201


def _csrf(c: TestClient) -> str:
    token = c.cookies.get("csrf_token")
    assert token
    return token


def _create_session_from_confirmed_fields(
    c: TestClient, doc_id: str, token: str
) -> tuple[str, str]:
    """Runs detection, confirms the first field, and creates a guided
    session from it — returns (session_id, session_ownership_token)."""
    headers = {"X-Document-Token": token} if token else {}
    detect_resp = c.post(
        f"/api/source-documents/{doc_id}/field-detection", headers=headers
    )
    assert detect_resp.status_code == 200
    field_id = detect_resp.json()["fields"][0]["fieldId"]

    patch_resp = c.patch(
        f"/api/source-documents/{doc_id}/field-detection/fields/{field_id}",
        headers=headers,
        json={"reviewStatus": "confirmed"},
    )
    assert patch_resp.status_code == 200

    session_resp = c.post(
        f"/api/source-documents/{doc_id}/field-detection/session",
        headers=headers,
        json={"language": "en", "outputLanguage": "en"},
    )
    assert session_resp.status_code == 200
    data = session_resp.json()
    return data["sessionId"], data["ownershipToken"]


# --- Anonymous access ---------------------------------------------------


def test_anonymous_field_detection_get_with_valid_token_succeeds(
    tmp_path: Path,
) -> None:
    doc_id, token = _upload_digital_document(client, tmp_path)
    client.post(
        f"/api/source-documents/{doc_id}/field-detection",
        headers={"X-Document-Token": token},
    )

    resp = client.get(
        f"/api/source-documents/{doc_id}/field-detection",
        headers={"X-Document-Token": token},
    )
    assert resp.status_code == 200


def test_anonymous_field_detection_get_without_token_returns_401(
    tmp_path: Path,
) -> None:
    doc_id, token = _upload_digital_document(client, tmp_path)
    client.post(
        f"/api/source-documents/{doc_id}/field-detection",
        headers={"X-Document-Token": token},
    )

    resp = client.get(f"/api/source-documents/{doc_id}/field-detection")
    assert resp.status_code == 401


def test_anonymous_ocr_get_without_token_returns_401(tmp_path: Path) -> None:
    doc_id, _token = _upload_digital_document(client, tmp_path)
    resp = client.get(f"/api/source-documents/{doc_id}/ocr")
    assert resp.status_code == 401


# --- Authenticated access (document created while logged in) -----------


def test_authenticated_owner_field_detection_get_succeeds(tmp_path: Path) -> None:
    _register(client, "owner@example.com")
    doc_id, token = _upload_digital_document(client, tmp_path)
    client.post(
        f"/api/source-documents/{doc_id}/field-detection",
        headers={"X-Document-Token": token},
    )

    # Cookie-only access, no document token at all — this is exactly the
    # request shape that previously returned 401 after Phase 12.
    resp = client.get(f"/api/source-documents/{doc_id}/field-detection")
    assert resp.status_code == 200


def test_authenticated_non_owner_field_detection_get_fails(tmp_path: Path) -> None:
    _register(client, "owner@example.com")
    doc_id, token = _upload_digital_document(client, tmp_path)
    client.post(
        f"/api/source-documents/{doc_id}/field-detection",
        headers={"X-Document-Token": token},
    )

    _register(other_client, "intruder@example.com")
    resp = other_client.get(f"/api/source-documents/{doc_id}/field-detection")
    assert resp.status_code == 401


def test_logged_in_user_can_still_use_valid_token_on_unclaimed_document(
    tmp_path: Path,
) -> None:
    """An anonymous document is untouched by someone merely being logged in
    in the same browser: the anonymous token must still work, and cookie-only
    access (no token) must NOT silently succeed just because a session
    exists — logging in never auto-claims anything."""
    doc_id, token = _upload_digital_document(client, tmp_path)
    client.post(
        f"/api/source-documents/{doc_id}/field-detection",
        headers={"X-Document-Token": token},
    )

    _register(client, "bystander@example.com")

    # Token-based access still works — the document was never claimed.
    with_token = client.get(
        f"/api/source-documents/{doc_id}/field-detection",
        headers={"X-Document-Token": token},
    )
    assert with_token.status_code == 200

    # Cookie-only access (no token) must fail — merely logging in must not
    # silently grant access to an anonymous document it never claimed.
    without_token = client.get(f"/api/source-documents/{doc_id}/field-detection")
    assert without_token.status_code == 401


# --- Claim transfers document (and therefore detection/OCR) ownership --


def test_claim_transfers_document_ownership_and_invalidates_old_token(
    tmp_path: Path,
) -> None:
    doc_id, doc_token = _upload_digital_document(client, tmp_path)
    session_id, session_token = _create_session_from_confirmed_fields(
        client, doc_id, doc_token
    )

    # Before claim: anonymous document token still works; a fresh cookie
    # session (not yet claimed) must not have access.
    _register(client, "claimer@example.com")
    csrf = _csrf(client)

    before_claim = client.get(
        f"/api/source-documents/{doc_id}/field-detection",
        headers={"X-Document-Token": doc_token},
    )
    assert before_claim.status_code == 200

    before_claim_cookie_only = client.get(
        f"/api/source-documents/{doc_id}/field-detection"
    )
    assert before_claim_cookie_only.status_code == 401

    # Claim the session — this must also transfer the linked document.
    claim_resp = client.post(
        "/api/applications/claim",
        json={"sessionId": session_id, "sessionToken": session_token},
        headers={"X-CSRF-Token": csrf},
    )
    assert claim_resp.status_code == 200

    # After claim: cookie-only access succeeds for field detection and OCR
    # eligibility endpoints (document itself), with no token at all.
    after_claim = client.get(f"/api/source-documents/{doc_id}/field-detection")
    assert after_claim.status_code == 200

    doc_after_claim = client.get(f"/api/source-documents/{doc_id}")
    assert doc_after_claim.status_code == 200

    # The old anonymous document token must no longer authorize access, for
    # a caller with no auth cookie at all.
    anonymous_caller = TestClient(app)
    old_token_after_claim = anonymous_caller.get(
        f"/api/source-documents/{doc_id}/field-detection",
        headers={"X-Document-Token": doc_token},
    )
    assert old_token_after_claim.status_code == 401


def test_claim_by_second_user_does_not_transfer_document_to_them(
    tmp_path: Path,
) -> None:
    """A rejected claim attempt (wrong token / already claimed by someone
    else) must never mutate document ownership."""
    doc_id, doc_token = _upload_digital_document(client, tmp_path)
    session_id, session_token = _create_session_from_confirmed_fields(
        client, doc_id, doc_token
    )

    _register(client, "first@example.com")
    csrf = _csrf(client)
    claimed = client.post(
        "/api/applications/claim",
        json={"sessionId": session_id, "sessionToken": session_token},
        headers={"X-CSRF-Token": csrf},
    )
    assert claimed.status_code == 200

    _register(other_client, "second@example.com")
    other_csrf = _csrf(other_client)
    rejected = other_client.post(
        "/api/applications/claim",
        json={"sessionId": session_id, "sessionToken": session_token},
        headers={"X-CSRF-Token": other_csrf},
    )
    assert rejected.status_code == 401

    # The document must still belong to the first user only.
    other_access = other_client.get(f"/api/source-documents/{doc_id}/field-detection")
    assert other_access.status_code == 401
