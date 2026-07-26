import logging
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import or_, select

from app.database.session import SessionLocal
from app.pdf.models import FormExport

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def cleanup_expired_exports() -> int:
    db = SessionLocal()
    now = datetime.now(UTC)
    logger.info("Starting cleanup of expired PDF exports...")

    try:
        # Find exports that are either marked expired/deleted but not updated,
        # or completed/failed/pending whose expires_at has passed.
        stmt = select(FormExport).where(
            or_(
                FormExport.expires_at < now,
                FormExport.status.in_(["expired", "deleted"]),
            )
        )
        exports = db.scalars(stmt).all()
        cleaned_count = 0

        for export in exports:
            # Skip if status is already marked deleted and the file was already cleaned
            if export.status == "deleted" and not Path(export.storage_path).exists():
                continue

            filepath = Path(export.storage_path)
            # Safe delete file if exists
            if filepath.exists() and filepath.is_file():
                try:
                    filepath.unlink()
                    logger.info(f"Deleted expired export file: {export.public_id}")
                except OSError as e:
                    logger.error(
                        f"Failed to delete file for export {export.public_id}: {str(e)}"
                    )
                    # Continue anyway to mark record

            # Mark status as deleted in database
            export.status = "deleted"
            cleaned_count += 1

        if cleaned_count > 0:
            db.commit()
            logger.info(
                f"Successfully cleaned up {cleaned_count} expired export records."
            )
        else:
            logger.info("No expired exports found to clean up.")

        # Cleanup expired source documents
        from app.documents.models import SourceDocument

        stmt_docs = select(SourceDocument).where(
            or_(
                SourceDocument.expires_at < now,
                SourceDocument.status.in_(["expired", "deleted"]),
            )
        )
        docs = db.scalars(stmt_docs).all()
        cleaned_docs_count = 0

        for doc in docs:
            # Skip if status is already marked deleted and the file was already cleaned
            if doc.status == "deleted" and not Path(doc.storage_path).exists():
                continue

            filepath = Path(doc.storage_path)
            # Safe delete file if exists
            if filepath.exists() and filepath.is_file():
                try:
                    filepath.unlink()
                    logger.info(
                        f"Deleted expired source document file: {doc.public_id}"
                    )
                except OSError as e:
                    logger.error(
                        f"Failed to delete file for source document {doc.public_id}: {str(e)}"
                    )

            doc.status = "deleted"
            cleaned_docs_count += 1

        if cleaned_docs_count > 0:
            db.commit()
            logger.info(
                f"Successfully cleaned up {cleaned_docs_count} expired source document records."
            )
        else:
            logger.info("No expired source documents found to clean up.")

        # Cleanup expired OCR results (rendered page images are removed inline
        # by OCRService after each run; here we only expire stale DB rows and
        # sweep any leftover per-run temp directories from crashed runs).
        from app.core.config import settings
        from app.ocr.models import OCRResult

        stmt_ocr = select(OCRResult).where(
            or_(
                OCRResult.expires_at < now,
                OCRResult.status.in_(["expired", "deleted"]),
            )
        )
        ocr_results = db.scalars(stmt_ocr).all()
        cleaned_ocr_count = 0

        for ocr_result in ocr_results:
            if ocr_result.status in ("expired", "deleted"):
                continue
            ocr_result.status = "expired"
            cleaned_ocr_count += 1

        if cleaned_ocr_count > 0:
            db.commit()
            logger.info(f"Successfully expired {cleaned_ocr_count} OCR result records.")
        else:
            logger.info("No expired OCR results found to clean up.")

        # Only sweep directories older than the OCR timeout: an in-progress run
        # never lives longer than that, so anything older is orphaned by a crash.
        render_root = Path(settings.OCR_RENDER_STORAGE_PATH)
        swept_dirs = 0
        if render_root.exists():
            now_ts = now.timestamp()
            for entry in render_root.iterdir():
                if not entry.is_dir():
                    continue
                try:
                    age_seconds = now_ts - entry.stat().st_mtime
                    if age_seconds < settings.OCR_TIMEOUT_SECONDS:
                        continue
                    for stray_file in entry.iterdir():
                        stray_file.unlink()
                    entry.rmdir()
                    swept_dirs += 1
                except OSError as e:
                    logger.error(
                        f"Failed to sweep OCR temp directory {entry}: {str(e)}"
                    )

        if swept_dirs > 0:
            logger.info(f"Swept {swept_dirs} leftover OCR temp render directories.")

        return 0

    except Exception as e:
        logger.error(f"Unexpected error during PDF cleanup: {str(e)}")
        db.rollback()
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    import sys

    sys.exit(cleanup_expired_exports())
