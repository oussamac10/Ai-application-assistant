"""Tests for smartphone camera image upload normalization (Phase S1-02).

Verifies:
- JPEG with EXIF Orientation=6 (90° CW) + EXIF GPS/Camera metadata rotates upright,
  strips 100% of EXIF/GPS tags, and normalizes into an A4 Portrait PDF ready for OCR.
- RGBA PNG and WebP uploads normalize cleanly onto A4 PDF pages.
- Spoofed magic bytes (e.g., .jpg containing HTML/text) and oversized pixel dimensions
  are deterministically rejected with DocumentValidationError.
"""

from __future__ import annotations

import io
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.core.config import settings
from app.database.session import SessionLocal
from app.documents.models import SourceDocument
from app.main import app
from app.storage.factory import get_storage_provider


@pytest.fixture()
def isolated_local_storage(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "storage"
    monkeypatch.setattr(settings, "STORAGE_PROVIDER", "local")
    monkeypatch.setattr(settings, "DOCUMENT_STORAGE_PATH", str(root))
    return root


def _build_exif_rotated_jpeg_with_gps() -> bytes:
    """Builds a landscape 800x400 raw JPEG whose top half is red and bottom half is white,
    tagged with EXIF Orientation=6 (90° CW -> upright 400x800 portrait with red on the RIGHT)
    plus sensitive camera/GPS EXIF tags that must be stripped on upload.
    """
    raw = Image.new("RGB", (800, 400), color=(255, 255, 255))
    for y in range(200):
        for x in range(800):
            raw.putpixel((x, y), (220, 20, 20))

    exif = raw.getexif()
    exif[0x0112] = 6  # Orientation = Rotate 90 CW
    exif[0x010F] = "Apple"  # Make
    exif[0x0110] = "iPhone 15 Pro Secret Camera"  # Model
    exif[0x9286] = "GPS:52.5200N,13.4050E"  # UserComment with location marker

    buf = io.BytesIO()
    raw.save(buf, format="JPEG", quality=92, exif=exif.tobytes())
    jpeg_bytes = buf.getvalue()
    assert b"iPhone 15 Pro Secret Camera" in jpeg_bytes
    assert b"GPS:52.5200N,13.4050E" in jpeg_bytes
    return jpeg_bytes


def test_jpeg_upload_transposes_exif_strips_metadata_and_normalizes_to_a4_pdf(
    isolated_local_storage: Path,
) -> None:
    jpeg_bytes = _build_exif_rotated_jpeg_with_gps()
    client = TestClient(app)

    resp = client.post(
        "/api/source-documents",
        files={"file": ("IMG_4021.JPG", jpeg_bytes, "image/jpeg")},
        data={"language": "ar", "privacyAccepted": "true"},
    )
    assert resp.status_code == 201, resp.text
    payload = resp.json()

    assert payload["status"] == "analyzed"
    analysis = payload["analysis"]
    assert analysis["pageCount"] == 1
    assert analysis["documentType"] == "scanned_pdf"
    assert analysis["isProbablyScanned"] is True
    assert analysis["hasEmbeddedImages"] is True
    assert analysis["nextStep"] == "ocr_required"

    db = SessionLocal()
    try:
        doc = (
            db.query(SourceDocument)
            .filter(SourceDocument.public_id == payload["documentId"])
            .one()
        )
        assert doc.content_type == "application/pdf"
        pdf_bytes = get_storage_provider().get_bytes(doc.storage_path)
    finally:
        db.close()

    assert pdf_bytes.startswith(b"%PDF")
    # Sensitive EXIF camera & GPS strings MUST NOT survive inside the stored PDF
    assert b"iPhone 15 Pro Secret Camera" not in pdf_bytes
    assert b"GPS:52.5200N,13.4050E" not in pdf_bytes
    assert b"Exif\x00\x00" not in pdf_bytes

    pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        assert len(pdf_doc) == 1
        page = pdf_doc[0]
        # After EXIF Orientation=6 (90° CW), 800x400 becomes 400x800 (portrait) -> A4 portrait (595 x 842 pt)
        assert abs(page.rect.width - 595.0) <= 1.5
        assert abs(page.rect.height - 842.0) <= 1.5

        # Verify pixel orientation: right half of rendered page has red ink, left half is white
        pix = page.get_pixmap(dpi=72, alpha=False)
        rendered = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
        mid_y = pix.height // 2
        right_sample = rendered.getpixel((int(pix.width * 0.75), mid_y))
        left_sample = rendered.getpixel((int(pix.width * 0.25), mid_y))
        assert (
            right_sample[0] > 180 and right_sample[1] < 80
        ), f"Expected red on right after 90° CW transpose, got {right_sample}"
        assert (
            left_sample[0] > 230 and left_sample[1] > 230 and left_sample[2] > 230
        ), f"Expected white on left after 90° CW transpose, got {left_sample}"
    finally:
        pdf_doc.close()


@pytest.mark.parametrize(
    ("fmt", "filename", "mime"),
    [
        ("PNG", "scan_alpha.png", "image/png"),
        ("WEBP", "camera_capture.webp", "image/webp"),
    ],
)
def test_png_rgba_and_webp_uploads_normalize_to_a4_pdf(
    isolated_local_storage: Path,
    fmt: str,
    filename: str,
    mime: str,
) -> None:
    # Landscape 600x400 image with alpha channel -> should normalize to A4 landscape (842 x 595 pt)
    img = Image.new("RGBA", (600, 400), color=(0, 0, 0, 0))
    for y in range(150, 250):
        for x in range(100, 500):
            img.putpixel((x, y), (20, 40, 120, 255))

    buf = io.BytesIO()
    img.save(buf, format=fmt)

    client = TestClient(app)
    resp = client.post(
        "/api/source-documents",
        files={"file": (filename, buf.getvalue(), mime)},
        data={"language": "de", "privacyAccepted": "true"},
    )
    assert resp.status_code == 201, resp.text
    payload = resp.json()
    assert payload["analysis"]["documentType"] == "scanned_pdf"
    assert payload["analysis"]["nextStep"] == "ocr_required"

    db = SessionLocal()
    try:
        doc = (
            db.query(SourceDocument)
            .filter(SourceDocument.public_id == payload["documentId"])
            .one()
        )
        pdf_bytes = get_storage_provider().get_bytes(doc.storage_path)
    finally:
        db.close()

    pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        page = pdf_doc[0]
        # Landscape image -> A4 landscape (842 x 595 pt)
        assert abs(page.rect.width - 842.0) <= 1.5
        assert abs(page.rect.height - 595.0) <= 1.5
        # Transparent corners should composite onto white (#FFFFFF), not black (#000000)
        pix = page.get_pixmap(dpi=72, alpha=False)
        corner_rgb = Image.frombytes(
            "RGB", (pix.width, pix.height), pix.samples
        ).getpixel((30, 30))
        assert corner_rgb[0] > 240 and corner_rgb[1] > 240 and corner_rgb[2] > 240
    finally:
        pdf_doc.close()


def test_spoofed_magic_bytes_and_oversized_pixel_bombs_are_rejected(
    isolated_local_storage: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = TestClient(app)

    # 1. Spoofed .jpg containing HTML text
    spoof_resp = client.post(
        "/api/source-documents",
        files={
            "file": (
                "evil.jpg",
                b"<html><script>alert(1)</script></html>",
                "image/jpeg",
            )
        },
        data={"language": "en", "privacyAccepted": "true"},
    )
    assert spoof_resp.status_code == 422
    assert spoof_resp.json()["error_code"] == "invalid_file_type"

    # 2. Image exceeding DOCUMENT_UPLOAD_MAX_IMAGE_PIXELS cap
    monkeypatch.setattr(
        settings, "DOCUMENT_UPLOAD_MAX_IMAGE_PIXELS", 10_000, raising=False
    )
    oversized = Image.new(
        "RGB", (200, 200), color=(255, 255, 255)
    )  # 40,000 px > 10,000
    buf = io.BytesIO()
    oversized.save(buf, format="PNG")

    bomb_resp = client.post(
        "/api/source-documents",
        files={"file": ("huge.png", buf.getvalue(), "image/png")},
        data={"language": "en", "privacyAccepted": "true"},
    )
    assert bomb_resp.status_code == 422
    assert bomb_resp.json()["error_code"] == "image_too_large"
