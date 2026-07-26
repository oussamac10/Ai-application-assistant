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
        db.commit()
        yield
    except Exception:
        db.rollback()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def use_mock_provider():
    original = settings.FIELD_DETECTION_PROVIDER
    settings.FIELD_DETECTION_PROVIDER = "mock"
    yield
    settings.FIELD_DETECTION_PROVIDER = original


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


def test_api_field_detection_flow(client: TestClient, tmp_path: Path) -> None:
    doc_id, token = _upload_digital_document(client, tmp_path)

    post_resp = client.post(
        f"/api/source-documents/{doc_id}/field-detection",
        headers={"X-Document-Token": token},
    )
    assert post_resp.status_code == 200
    data = post_resp.json()
    assert data["status"] == "completed"
    assert data["provider"] == "mock"
    assert data["sourceType"] == "native"
    assert data["fieldCount"] >= 1
    assert data["fields"][0]["reviewStatus"] == "pending_review"

    get_resp = client.get(
        f"/api/source-documents/{doc_id}/field-detection",
        headers={"X-Document-Token": token},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "completed"


def test_api_field_detection_requires_valid_token(
    client: TestClient, tmp_path: Path
) -> None:
    doc_id, _token = _upload_digital_document(client, tmp_path)

    resp = client.post(
        f"/api/source-documents/{doc_id}/field-detection",
        headers={"X-Document-Token": "invalid"},
    )
    assert resp.status_code == 401


def test_api_field_detection_get_before_request_returns_404(
    client: TestClient, tmp_path: Path
) -> None:
    doc_id, token = _upload_digital_document(client, tmp_path)

    resp = client.get(
        f"/api/source-documents/{doc_id}/field-detection",
        headers={"X-Document-Token": token},
    )
    assert resp.status_code == 404


def test_api_field_detection_rejects_supported_template(
    client: TestClient, tmp_path: Path
) -> None:
    pdf_path = tmp_path / "template.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.drawString(
        100,
        750,
        "AI Form Assistant Basic Registration Version 1.0 (Phase 8 Predefined)",
    )
    form = c.acroForm
    for idx, field_name in enumerate(
        [
            "first_name",
            "last_name",
            "date_of_birth",
            "email",
            "country",
            "marital_status",
        ]
    ):
        form.textfield(
            name=field_name,
            tooltip=field_name,
            x=200,
            y=600 - (idx * 50),
            width=200,
            height=20,
            value="",
        )
    c.showPage()
    c.save()

    with open(pdf_path, "rb") as f:
        response = client.post(
            "/api/source-documents",
            data={"language": "en", "outputLanguage": "en", "privacyAccepted": "true"},
            files={"file": ("template.pdf", f, "application/pdf")},
        )
    doc_id = response.json()["documentId"]
    token = response.json()["ownershipToken"]

    resp = client.post(
        f"/api/source-documents/{doc_id}/field-detection",
        headers={"X-Document-Token": token},
    )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "supported_template_detected"
