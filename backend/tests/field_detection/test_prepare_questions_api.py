"""API-level tests for POST /api/source-documents/{id}/prepare-questions
(Phase 13) — the endpoint the normal-user upload flow calls. Exercises the
route/schema layer end-to-end; confidence-routing decision logic itself is
covered by test_confidence.py, and the composed-service behavior by
test_orchestration.py."""

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


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_db() -> Generator[None, None, None]:
    db = SessionLocal()
    try:
        db.execute(text("TRUNCATE TABLE source_documents CASCADE"))
        db.execute(text("TRUNCATE TABLE form_templates CASCADE"))
        db.execute(text("TRUNCATE TABLE form_sessions CASCADE"))
        db.commit()
        yield
    except Exception:
        db.rollback()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def use_mock_providers():
    original_fd = settings.FIELD_DETECTION_PROVIDER
    original_ocr = settings.OCR_PROVIDER
    settings.FIELD_DETECTION_PROVIDER = "mock"
    settings.OCR_PROVIDER = "mock"
    yield
    settings.FIELD_DETECTION_PROVIDER = original_fd
    settings.OCR_PROVIDER = original_ocr


def _create_digital_pdf(filepath: str) -> None:
    c = canvas.Canvas(filepath, pagesize=letter)
    c.drawString(100, 700, "Just some unmatched content")
    c.showPage()
    c.save()


def _upload_digital_document(client: TestClient, tmp_path: Path) -> tuple[str, str]:
    pdf_path = tmp_path / "digital.pdf"
    _create_digital_pdf(str(pdf_path))
    with open(pdf_path, "rb") as f:
        response = client.post(
            "/api/source-documents",
            data={"language": "en", "outputLanguage": "en", "privacyAccepted": "true"},
            files={"file": ("digital.pdf", f, "application/pdf")},
        )
    assert response.status_code == 201
    data = response.json()
    assert data["analysis"]["nextStep"] == "dynamic_field_detection"
    return data["documentId"], data["ownershipToken"]


def test_prepare_questions_returns_ready_session_with_no_technical_fields(
    client: TestClient, tmp_path: Path
) -> None:
    doc_id, token = _upload_digital_document(client, tmp_path)

    resp = client.post(
        f"/api/source-documents/{doc_id}/prepare-questions",
        headers={"X-Document-Token": token},
        json={"language": "en", "outputLanguage": "en"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert data["sessionId"]
    assert data["ownershipToken"]

    # The normal-user response never exposes technical detection internals.
    serialized = str(data)
    for forbidden in ("confidence", "provider", "boundingBox", "fieldId", "candidate"):
        assert forbidden not in serialized


def test_prepare_questions_requires_valid_token(
    client: TestClient, tmp_path: Path
) -> None:
    doc_id, _token = _upload_digital_document(client, tmp_path)

    resp = client.post(
        f"/api/source-documents/{doc_id}/prepare-questions",
        headers={"X-Document-Token": "invalid"},
        json={"language": "en", "outputLanguage": "en"},
    )
    assert resp.status_code == 401


def test_prepare_questions_idempotent_returns_same_session(
    client: TestClient, tmp_path: Path
) -> None:
    doc_id, token = _upload_digital_document(client, tmp_path)

    first = client.post(
        f"/api/source-documents/{doc_id}/prepare-questions",
        headers={"X-Document-Token": token},
        json={"language": "en", "outputLanguage": "en"},
    )
    second = client.post(
        f"/api/source-documents/{doc_id}/prepare-questions",
        headers={"X-Document-Token": token},
        json={"language": "en", "outputLanguage": "en"},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["sessionId"] == second.json()["sessionId"]
    assert second.json()["reusedExistingSession"] is True
