import hashlib
from pathlib import Path


class PDFValidationError(Exception):
    pass


class PDFExportValidator:
    def __init__(self, expected_page_count: int = 1) -> None:
        self.expected_page_count = expected_page_count

    def validate(self, filepath: Path) -> str:
        """
        Validate the generated PDF file.
        Returns the SHA-256 checksum of the file if valid, raises PDFValidationError otherwise.
        """
        # 1. Check file exists
        if not filepath.exists():
            raise PDFValidationError("Generated PDF file does not exist.")

        # 2. Check file size > 0
        if filepath.stat().st_size == 0:
            raise PDFValidationError("Generated PDF file is empty (0 bytes).")

        # 3. Check PDF signature
        try:
            with open(filepath, "rb") as f:
                header = f.read(5)
            if header != b"%PDF-":
                raise PDFValidationError(
                    "Generated file does not have a valid PDF header signature."
                )
        except OSError as e:
            raise PDFValidationError(f"Failed to read generated PDF: {str(e)}") from e

        # 4. Generate SHA-256 checksum
        sha256 = hashlib.sha256()
        try:
            with open(filepath, "rb") as f:
                while chunk := f.read(8192):
                    sha256.update(chunk)
        except OSError as e:
            raise PDFValidationError(f"Failed to compute PDF checksum: {str(e)}") from e

        return sha256.hexdigest()
