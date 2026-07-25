import os
import re
import uuid
from pathlib import Path

from app.core.config import settings


def sanitize_filename(filename: str) -> str:
    """Sanitizes the original filename to keep it safe for metadata."""
    base = os.path.basename(filename)
    # Replace non-alphanumeric characters (except dots, dashes, underscores) with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9._-]', '_', base)
    # Trim leading/trailing dots/dashes/underscores
    sanitized = sanitized.strip("._-")
    return sanitized if sanitized else "uploaded_document.pdf"


class DocumentStorage:
    def __init__(self, storage_dir: str = settings.DOCUMENT_STORAGE_PATH):
        self.storage_dir = Path(storage_dir)
        os.makedirs(self.storage_dir, exist_ok=True)

    def generate_storage_path(self) -> Path:
        """Generates a random secure UUID-based filename path."""
        filename = f"{uuid.uuid4()}.pdf"
        return self.storage_dir / filename

    def delete_file(self, path_str: str) -> bool:
        """Deletes a file if it resides within the configured storage directory."""
        if not path_str:
            return False
        path = Path(path_str)
        try:
            resolved_root = self.storage_dir.resolve()
            resolved_path = path.resolve()
            # Security check: Ensure the path is inside the storage root
            if resolved_root in resolved_path.parents:
                if resolved_path.is_file():
                    os.unlink(resolved_path)
                    return True
        except Exception:
            pass
        return False
