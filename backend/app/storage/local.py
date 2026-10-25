from __future__ import annotations

import os
import shutil
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.core.config import settings
from app.storage.base import StorageNamespace


class LocalStorageProvider:
    """Filesystem-backed StorageProvider with strict root-boundary enforcement."""

    provider_name = "local"

    def __init__(
        self,
        documents_dir: str | None = None,
        exports_dir: str | None = None,
    ) -> None:
        self.documents_dir = Path(documents_dir or settings.DOCUMENT_STORAGE_PATH)
        self.exports_dir = Path(exports_dir or settings.PDF_EXPORT_DIRECTORY)
        self.documents_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def _root_for(self, namespace: StorageNamespace) -> Path:
        if namespace == "documents":
            self.documents_dir.mkdir(parents=True, exist_ok=True)
            return self.documents_dir
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        return self.exports_dir

    def save_file(
        self,
        namespace: StorageNamespace,
        filename: str,
        source_path: Path,
        content_type: str = "application/pdf",
    ) -> str:
        safe_name = os.path.basename(filename)
        if not safe_name or safe_name in (".", ".."):
            raise ValueError("Invalid storage filename.")
        root = self._root_for(namespace).resolve()
        dest = (root / safe_name).resolve()
        if root not in dest.parents:
            raise ValueError("Storage path escapes configured root directory.")
        src_resolved = source_path.resolve()
        if src_resolved != dest:
            shutil.copyfile(src_resolved, dest)
        return str(dest)

    def exists(self, storage_ref: str) -> bool:
        if not storage_ref or storage_ref.startswith("s3://"):
            return False
        return Path(storage_ref).is_file()

    def get_bytes(self, storage_ref: str) -> bytes:
        if not self.exists(storage_ref):
            raise FileNotFoundError(f"Stored file not found: {storage_ref}")
        return Path(storage_ref).read_bytes()

    @contextmanager
    def local_path(self, storage_ref: str) -> Iterator[Path]:
        if not self.exists(storage_ref):
            raise FileNotFoundError(f"Stored file not found: {storage_ref}")
        yield Path(storage_ref)

    def delete(self, storage_ref: str) -> bool:
        if not storage_ref or storage_ref.startswith("s3://"):
            return False
        try:
            resolved_path = Path(storage_ref).resolve()
            allowed_roots = (
                self.documents_dir.resolve(),
                self.exports_dir.resolve(),
            )
            if any(root in resolved_path.parents for root in allowed_roots):
                if resolved_path.is_file():
                    resolved_path.unlink()
                    return True
        except OSError:
            return False
        return False

    def presigned_download_url(
        self,
        storage_ref: str,
        filename: str,
        expires_in_seconds: int = 300,
    ) -> str | None:
        return None
