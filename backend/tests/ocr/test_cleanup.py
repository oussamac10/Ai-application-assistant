import os
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import text

from app.commands.cleanup_expired_exports import cleanup_expired_exports
from app.core.config import settings
from app.database.session import SessionLocal
from app.documents.models import SourceDocument
from app.ocr.models import OCRResult


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


def _create_source_document(db, public_id: str, storage_path: Path) -> SourceDocument:
    storage_path.write_bytes(b"%PDF-1.4 fake content")
    doc = SourceDocument(
        public_id=public_id,
        ownership_token_hash="fakehash",
        original_filename="doc.pdf",
        sanitized_filename="doc.pdf",
        storage_path=str(storage_path),
        content_type="application/pdf",
        size_bytes=1000,
        checksum_sha256="fakechecksum",
        status="analyzed",
        expires_at=datetime.now(UTC) + timedelta(hours=24),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def test_cleanup_expires_stale_ocr_results(tmp_path: Path) -> None:
    db = SessionLocal()
    try:
        doc = _create_source_document(db, "ocr-cleanup-doc", tmp_path / "doc.pdf")

        ocr_result = OCRResult(
            source_document_id=doc.id,
            status="completed",
            provider_name="mock",
            provider_version="1",
            language="en",
            page_count=1,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
            created_at=datetime.now(UTC) - timedelta(hours=25),
            updated_at=datetime.now(UTC) - timedelta(hours=25),
        )
        db.add(ocr_result)
        db.commit()

        res = cleanup_expired_exports()
        assert res == 0

        db.refresh(ocr_result)
        assert ocr_result.status == "expired"
    finally:
        db.close()


def test_cleanup_sweeps_orphaned_render_temp_dirs() -> None:
    render_root = Path(settings.OCR_RENDER_STORAGE_PATH)
    render_root.mkdir(parents=True, exist_ok=True)

    stale_dir = render_root / "stale-ocr-run"
    stale_dir.mkdir(exist_ok=True)
    stray_file = stale_dir / "page-1.png"
    stray_file.write_bytes(b"fake-image-bytes")

    old_time = datetime.now(UTC).timestamp() - (settings.OCR_TIMEOUT_SECONDS + 3600)
    os.utime(stale_dir, (old_time, old_time))

    fresh_dir = render_root / "fresh-ocr-run"
    fresh_dir.mkdir(exist_ok=True)
    (fresh_dir / "page-1.png").write_bytes(b"fake-image-bytes")

    res = cleanup_expired_exports()
    assert res == 0

    assert not stale_dir.exists()
    assert fresh_dir.exists()

    for f in fresh_dir.iterdir():
        f.unlink()
    fresh_dir.rmdir()
