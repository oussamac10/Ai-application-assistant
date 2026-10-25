from __future__ import annotations

from app.core.config import settings
from app.storage.base import StorageProvider
from app.storage.local import LocalStorageProvider
from app.storage.s3 import S3StorageProvider


def get_storage_provider() -> StorageProvider:
    """Builds the configured StorageProvider (`local` or EU `s3`)."""
    if settings.STORAGE_PROVIDER == "s3":
        return S3StorageProvider(
            endpoint_url=settings.S3_ENDPOINT_URL or "",
            region=settings.S3_REGION,
            bucket=settings.S3_BUCKET or "",
            access_key_id=settings.S3_ACCESS_KEY_ID or "",
            secret_access_key=settings.S3_SECRET_ACCESS_KEY or "",
            key_prefix=settings.S3_KEY_PREFIX,
            timeout_seconds=settings.S3_TIMEOUT_SECONDS,
        )
    return LocalStorageProvider(
        documents_dir=settings.DOCUMENT_STORAGE_PATH,
        exports_dir=settings.PDF_EXPORT_DIRECTORY,
    )
