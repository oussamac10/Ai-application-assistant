import os
import re
import uuid
from pathlib import Path

from app.core.config import settings
from app.storage import factory as storage_factory


def sanitize_filename(filename: str) -> str:
    """Sanitizes the original filename to keep it safe for metadata."""
    base = os.path.basename(filename)
    sanitized = re.sub(r"[^a-zA-Z0-9._-]", "_", base)
    sanitized = sanitized.strip("._-")
    return sanitized if sanitized else "uploaded_document.pdf"


class DocumentStorage:
    def __init__(self, storage_dir: str | None = None):
        self.storage_dir = Path(storage_dir or settings.DOCUMENT_STORAGE_PATH)
        os.makedirs(self.storage_dir, exist_ok=True)

    def generate_storage_path(self) -> Path:
        """Generates a random secure UUID-based local staging path."""
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        filename = f"{uuid.uuid4()}.pdf"
        return self.storage_dir / filename

    def persist_uploaded_file(self, staged_path: Path) -> str:
        """Saves a validated staged PDF via the active StorageProvider."""
        provider = storage_factory.get_storage_provider()
        ref = provider.save_file(
            namespace="documents",
            filename=staged_path.name,
            source_path=staged_path,
            content_type="application/pdf",
        )
        if ref.startswith("s3://") and staged_path.is_file():
            try:
                staged_path.unlink()
            except OSError:
                pass
        return ref

    def delete_file(self, path_str: str) -> bool:
        """Deletes a stored document via StorageProvider or local storage root."""
        if not path_str:
            return False
        if path_str.startswith("s3://"):
            return storage_factory.get_storage_provider().delete(path_str)
        path = Path(path_str)
        try:
            resolved_root = self.storage_dir.resolve()
            resolved_path = path.resolve()
            if resolved_root in resolved_path.parents and resolved_path.is_file():
                os.unlink(resolved_path)
                return True
        except Exception:
            pass
        return storage_factory.get_storage_provider().delete(path_str)
