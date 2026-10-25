from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import fitz
import httpx
import pytest
from fastapi.testclient import TestClient

from app.commands.cleanup_expired_exports import cleanup_expired_exports
from app.core.config import Settings
from app.database.session import SessionLocal
from app.documents.service import SourceDocumentService
from app.field_detection.models import DetectedField, FieldDetectionResult
from app.forms.models import FormField, FormTemplate, FormVersion
from app.main import app
from app.pdf.services import PDFExportService
from app.sessions.services import SessionService
from app.storage.factory import get_storage_provider
from app.storage.local import LocalStorageProvider
from app.storage.s3 import S3StorageProvider


def _make_sample_pdf(path: Path, label_text: str = "Vorname: ________") -> bytes:
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text(fitz.Point(72, 100), label_text, fontsize=11)
    data = bytes(doc.tobytes())
    doc.close()
    path.write_bytes(data)
    return data


class _InMemoryS3Transport(httpx.BaseTransport):
    """Deterministic in-memory S3-compatible HTTP transport verifying SigV4 headers."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.requests: list[httpx.Request] = []

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        auth = request.headers.get("Authorization", "")
        assert auth.startswith(
            "AWS4-HMAC-SHA256 Credential="
        ), f"Missing SigV4 Authorization header: {auth}"
        assert "x-amz-date" in {k.lower() for k in request.headers.keys()}
        assert "x-amz-content-sha256" in {k.lower() for k in request.headers.keys()}

        path_key = request.url.path.lstrip("/")
        method = request.method.upper()

        if method == "PUT":
            self.objects[path_key] = request.read()
            return httpx.Response(200, headers={"ETag": '"mock-etag"'})
        if method == "HEAD":
            if path_key in self.objects:
                return httpx.Response(
                    200,
                    headers={"Content-Length": str(len(self.objects[path_key]))},
                )
            return httpx.Response(404)
        if method == "GET":
            if path_key in self.objects:
                return httpx.Response(
                    200,
                    content=self.objects[path_key],
                    headers={"Content-Type": "application/pdf"},
                )
            return httpx.Response(404, content=b"<Error><Code>NoSuchKey</Code></Error>")
        if method == "DELETE":
            self.objects.pop(path_key, None)
            return httpx.Response(204)
        return httpx.Response(405)


def test_local_storage_provider_lifecycle_and_traversal_guard(tmp_path: Path) -> None:
    docs_dir = tmp_path / "docs"
    exports_dir = tmp_path / "exports"
    outside_file = tmp_path / "secret.pdf"
    outside_file.write_bytes(b"%PDF-1.4 secret")

    src = tmp_path / "incoming.pdf"
    payload = _make_sample_pdf(src)

    provider = LocalStorageProvider(
        documents_dir=str(docs_dir),
        exports_dir=str(exports_dir),
    )
    ref = provider.save_file("documents", "test-doc.pdf", src)
    assert Path(ref).parent == docs_dir.resolve()
    assert provider.exists(ref) is True
    assert provider.get_bytes(ref) == payload

    with provider.local_path(ref) as local_p:
        assert local_p.is_file()
        assert local_p.read_bytes() == payload

    # Refuses deleting files outside managed roots
    assert provider.delete(str(outside_file)) is False
    assert outside_file.exists() is True

    # Deletes managed file cleanly
    assert provider.delete(ref) is True
    assert provider.exists(ref) is False


def test_s3_storage_provider_sigv4_roundtrip_and_temp_cleanup(tmp_path: Path) -> None:
    transport = _InMemoryS3Transport()
    client = httpx.Client(transport=transport)
    provider = S3StorageProvider(
        endpoint_url="https://fsn1.your-objectstorage.com",
        region="eu-central",
        bucket="ai-form-vault",
        access_key_id="AKIAIOSFODNN7EXAMPLE",
        secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        key_prefix="prod/",
        http_client=client,
    )

    src = tmp_path / "scan.pdf"
    payload = _make_sample_pdf(src)

    ref = provider.save_file("documents", "abc-123.pdf", src)
    assert ref == "s3://ai-form-vault/prod/documents/abc-123.pdf"
    assert provider.exists(ref) is True
    assert provider.get_bytes(ref) == payload

    temp_seen: Path | None = None
    with provider.local_path(ref) as materialized:
        temp_seen = materialized
        assert materialized.is_file()
        assert materialized.read_bytes() == payload
    assert temp_seen is not None
    assert not temp_seen.exists(), "Temporary S3 download must be cleaned up on exit"

    presigned = provider.presigned_download_url(
        ref, filename="completed-form.pdf", expires_in_seconds=300
    )
    assert presigned is not None
    assert "X-Amz-Algorithm=AWS4-HMAC-SHA256" in presigned
    assert "X-Amz-Expires=300" in presigned
    assert "X-Amz-Signature=" in presigned

    assert provider.delete(ref) is True
    assert provider.exists(ref) is False


def test_s3_settings_fail_fast_when_incomplete() -> None:
    with pytest.raises(ValueError, match="S3_BUCKET"):
        Settings(
            STORAGE_PROVIDER="s3",
            S3_ENDPOINT_URL="https://fsn1.your-objectstorage.com",
            S3_BUCKET="",
            S3_ACCESS_KEY_ID="key",
            S3_SECRET_ACCESS_KEY="secret",
        )


def test_end_to_end_upload_export_download_and_cleanup_over_s3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    transport = _InMemoryS3Transport()
    s3_provider = S3StorageProvider(
        endpoint_url="https://fsn1.your-objectstorage.com",
        region="eu-central",
        bucket="ai-form-vault",
        access_key_id="AKIAIOSFODNN7EXAMPLE",
        secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        key_prefix="env/",
        http_client=httpx.Client(transport=transport),
    )
    monkeypatch.setattr("app.storage.factory.get_storage_provider", lambda: s3_provider)
    assert get_storage_provider() is not None  # sanity import usage

    sample_pdf_path = tmp_path / "upload.pdf"
    pdf_bytes = _make_sample_pdf(sample_pdf_path, "Vorname: ____________")

    db = SessionLocal()
    try:
        doc_service = SourceDocumentService(db)
        doc, doc_token = doc_service.upload_and_analyze(
            filename="meldeschein.pdf",
            content_type="application/pdf",
            file_chunks=[pdf_bytes],
            privacy_accepted=True,
            user_language="ar",
            output_language="de",
        )
        assert doc.storage_path.startswith("s3://ai-form-vault/env/documents/")
        assert s3_provider.exists(doc.storage_path) is True

        # Attach completed detection + dynamic FormVersion + ready_for_export session
        det = FieldDetectionResult(
            source_document_id=doc.id,
            status="completed",
            source_type="native",
            provider_name="local",
            provider_version="1.0",
            field_count=1,
            average_confidence=0.95,
            analysis_version=1,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        db.add(det)
        db.flush()
        df = DetectedField(
            detection_result_id=det.id,
            page_number=1,
            label="Vorname",
            normalized_name="first_name",
            field_type="string",
            required=True,
            confidence=0.95,
            source="native",
            display_order=0,
            review_status="confirmed",
            input_bounding_box={"x": 150.0, "y": 88.0, "width": 160.0, "height": 16.0},
        )
        db.add(df)

        tmpl = FormTemplate(
            key=f"dyn-s3-{doc.public_id[:8]}",
            name="Meldeschein",
        )
        db.add(tmpl)
        db.flush()
        ver = FormVersion(
            form_template_id=tmpl.id,
            version_number=1,
            status="published",
            origin="dynamic_detection",
            source_language="de",
            supported_output_languages=["de"],
        )
        db.add(ver)
        db.flush()
        ff = FormField(
            form_version_id=ver.id,
            key="first_name",
            field_type="string",
            position=0,
            required=True,
            requiredness="required",
        )
        db.add(ff)
        db.commit()

        sess_service = SessionService(db)
        session, sess_token = sess_service.create_session(
            form_version_id=ver.id,
            user_language="ar",
            output_language="de",
            source_document_id=doc.id,
        )
        from app.answers.models import FormAnswer

        ans = FormAnswer(
            session_id=session.id,
            field_id=ff.id,
            original_language="ar",
            original_answer="Oussama",
            normalized_value={"value": "Oussama"},
            output_value="Oussama",
            status="confirmed",
            validation_status="valid",
            translation_status="not_required",
            confirmed_by_user=True,
        )
        db.add(ans)
        session.status = "ready_for_export"
        db.commit()

        # Render dynamic overlay export straight to S3
        pdf_service = PDFExportService(db)
        export = pdf_service.create_export(session.public_id, sess_token)
        assert export.status == "completed"
        assert export.storage_path.startswith("s3://ai-form-vault/env/exports/")
        assert s3_provider.exists(export.storage_path) is True

        # Download via FastAPI route streams S3 PDF bytes cleanly
        client = TestClient(app)
        resp = client.get(
            f"/api/form-exports/{export.public_id}/download",
            headers={"X-Session-Token": sess_token},
        )
        assert resp.status_code == 200
        assert resp.content.startswith(b"%PDF")

        # Expire both anonymous records and verify cleanup_expired_exports deletes S3 blobs
        past_created = datetime.now(UTC) - timedelta(hours=3)
        past_expired = datetime.now(UTC) - timedelta(hours=1)
        export.created_at = past_created
        export.expires_at = past_expired
        doc.created_at = past_created
        doc.expires_at = past_expired
        db.commit()

        cleanup_expired_exports()
        assert s3_provider.exists(export.storage_path) is False
        assert s3_provider.exists(doc.storage_path) is False
    finally:
        db.close()
