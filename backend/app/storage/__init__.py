"""Pluggable private object & file storage adapters (Phase S1-01)."""

from app.storage.base import StorageNamespace, StorageProvider
from app.storage.factory import get_storage_provider
from app.storage.local import LocalStorageProvider
from app.storage.s3 import S3StorageProvider

__all__ = [
    "LocalStorageProvider",
    "S3StorageProvider",
    "StorageNamespace",
    "StorageProvider",
    "get_storage_provider",
]
