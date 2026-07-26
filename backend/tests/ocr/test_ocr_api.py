from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import text

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


def _create_scanned_pdf(filepath: str, tmp_path: Path) -> None:
    jpeg_path = tmp_path / "temp_image.jpg"
    img = Image.new("RGB", (100, 100), color="blue")
    img.save(jpeg_path, "JPEG")

    c = canvas.Canvas(filepath, pagesize=letter)
    c.drawImage(str(jpeg_path), 0, 0, width=612, height=792)
    c.showPage()
    c.save()


def _upload_scanned_document(client: TestClient, tmp_path: Path) -> tuple[str, str]:
    pdf_path = tmp_path / "scanned.pdf"
    _create_scanned_pdf(str(pdf_path), tmp_path)

    with open(pdf_path, "rb") as f:
        response = client.post(
            "/api/source-documents",
            data={"language": "en", "outputLanguage": "en", "privacyAccepted": "true"},
            files={"file": ("scanned.pdf", f, "application/pdf")},
        )
    assert response.status_code == 201
    data = response.json()
    assert data["analysis"]["nextStep"] == "ocr_required"
    return data["documentId"], data["ownershipToken"]


def test_api_ocr_flow(client: TestClient, tmp_path: Path) -> None:
    doc_id, token = _upload_scanned_document(client, tmp_path)

    post_resp = client.post(
        f"/api/source-documents/{doc_id}/ocr",
        headers={"X-Document-Token": token},
        json={"language": "en"},
    )
    assert post_resp.status_code == 200
    data = post_resp.json()
    assert data["status"] == "completed"
    assert data["provider"] == "mock"
    assert data["pageCount"] == 1
    assert len(data["pages"]) == 1
    assert data["pages"][0]["text"]

    get_resp = client.get(
        f"/api/source-documents/{doc_id}/ocr",
        headers={"X-Document-Token": token},
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["status"] == "completed"


def test_api_ocr_requires_valid_token(client: TestClient, tmp_path: Path) -> None:
    doc_id, _token = _upload_scanned_document(client, tmp_path)

    resp = client.post(
        f"/api/source-documents/{doc_id}/ocr",
        headers={"X-Document-Token": "invalid"},
        json={"language": "en"},
    )
    assert resp.status_code == 401


def test_api_ocr_get_before_request_returns_404(
    client: TestClient, tmp_path: Path
) -> None:
    doc_id, token = _upload_scanned_document(client, tmp_path)

    resp = client.get(
        f"/api/source-documents/{doc_id}/ocr",
        headers={"X-Document-Token": token},
    )
    assert resp.status_code == 404


def test_api_ocr_rejects_document_not_requiring_ocr(
    client: TestClient, tmp_path: Path
) -> None:
    pdf_path = tmp_path / "digital.pdf"
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    c.drawString(100, 750, "Digital content")
    c.showPage()
    c.save()

    with open(pdf_path, "rb") as f:
        response = client.post(
            "/api/source-documents",
            data={"language": "en", "outputLanguage": "en", "privacyAccepted": "true"},
            files={"file": ("digital.pdf", f, "application/pdf")},
        )
    doc_id = response.json()["documentId"]
    token = response.json()["ownershipToken"]

    resp = client.post(
        f"/api/source-documents/{doc_id}/ocr",
        headers={"X-Document-Token": token},
        json={"language": "en"},
    )
    assert resp.status_code == 422
    assert resp.json()["error_code"] == "ocr_not_required"
