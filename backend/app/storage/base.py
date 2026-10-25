from __future__ import annotations

from contextlib import AbstractContextManager
from pathlib import Path
from typing import Literal, Protocol

StorageNamespace = Literal["documents", "exports"]


class StorageProvider(Protocol):
    """Protocol for private document & PDF export persistence."""

    provider_name: str

    def save_file(
        self,
        namespace: StorageNamespace,
        filename: str,
        source_path: Path,
        content_type: str = "application/pdf",
    ) -> str:
        """Persists `source_path` under `namespace` and returns an opaque storage reference."""
        ...

    def exists(self, storage_ref: str) -> bool:
        """Returns True when `storage_ref` exists and is readable."""
        ...

    def get_bytes(self, storage_ref: str) -> bytes:
        """Reads raw bytes for `storage_ref`."""
        ...

    def local_path(self, storage_ref: str) -> AbstractContextManager[Path]:
        """Context manager yielding a local filesystem `Path` for parsers/renderers."""
        ...

    def delete(self, storage_ref: str) -> bool:
        """Deletes `storage_ref` if present and returns True on deletion."""
        ...

    def presigned_download_url(
        self,
        storage_ref: str,
        filename: str,
        expires_in_seconds: int = 300,
    ) -> str | None:
        """Optional short-lived signed download URL when backed by object storage."""
        ...
