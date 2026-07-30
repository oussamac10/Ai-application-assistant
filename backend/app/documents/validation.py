from typing import Any, cast

import pypdf

from app.documents.errors import DocumentValidationError


def validate_pdf_signature(filepath: str) -> None:
    """Verifies that the file starts with the correct PDF signature bytes."""
    try:
        with open(filepath, "rb") as f:
            header = f.read(4)
            if header != b"%PDF":
                raise DocumentValidationError(
                    "Invalid file signature. File is not a PDF.",
                    "invalid_file_type",
                )
    except OSError as e:
        raise DocumentValidationError(
            f"Could not read file: {str(e)}",
            "malformed_pdf",
        ) from e


def validate_pdf_structure(filepath: str, max_pages: int) -> None:
    """Attempts to parse the PDF to verify it is readable and within page limits."""
    try:
        reader = pypdf.PdfReader(filepath)

        # Check if encrypted or password protected
        if reader.is_encrypted:
            raise DocumentValidationError(
                "PDF is encrypted or password-protected.",
                "encrypted_pdf",
            )

        page_count = len(reader.pages)
        if page_count == 0:
            raise DocumentValidationError(
                "PDF contains zero pages.",
                "malformed_pdf",
            )
        if page_count > max_pages:
            raise DocumentValidationError(
                f"PDF exceeds the maximum page limit of {max_pages} pages.",
                "too_many_pages",
            )

        # Touch page objects to ensure structural integrity
        for page in reader.pages:
            if not page.mediabox:
                raise DocumentValidationError(
                    "PDF page is missing layout dimensions.",
                    "malformed_pdf",
                )
    except pypdf.errors.FileNotDecryptedError as e:
        raise DocumentValidationError(
            "PDF is password-protected or encrypted.",
            "password_protected_pdf",
        ) from e
    except DocumentValidationError:
        raise
    except Exception as e:
        raise DocumentValidationError(
            f"Malformed PDF or corrupted structure: {str(e)}",
            "malformed_pdf",
        ) from e


def validate_pdf_safety(filepath: str) -> None:
    """Scans the PDF catalog and pages for active or dangerous content."""
    try:
        reader = pypdf.PdfReader(filepath)
        catalog = reader.trailer.get("/Root")
        if not catalog:
            return

        catalog_obj = (
            catalog.get_object() if hasattr(catalog, "get_object") else catalog
        )

        # Check for active actions at root level
        if "/JavaScript" in catalog_obj or "/JS" in catalog_obj:
            raise DocumentValidationError(
                "PDF contains embedded JavaScript.",
                "unsupported_pdf_feature",
            )
        if "/OpenAction" in catalog_obj:
            raise DocumentValidationError(
                "PDF contains automatic OpenAction triggers.",
                "unsupported_pdf_feature",
            )
        if "/AA" in catalog_obj:
            raise DocumentValidationError(
                "PDF contains active Additional Actions.",
                "unsupported_pdf_feature",
            )

        # Check for embedded files or names list JavaScript
        names = catalog_obj.get("/Names")
        if names:
            names_obj = names.get_object() if hasattr(names, "get_object") else names
            if "/EmbeddedFiles" in names_obj or "/JavaScript" in names_obj:
                raise DocumentValidationError(
                    "PDF contains embedded files or JavaScript attachments.",
                    "unsupported_pdf_feature",
                )

        # Check pages and annotations
        for page in reader.pages:
            page_obj = page.get_object() if hasattr(page, "get_object") else page
            if page_obj is None:
                continue
            if "/AA" in cast(Any, page_obj):
                raise DocumentValidationError(
                    "Page contains active Additional Actions.",
                    "unsupported_pdf_feature",
                )

            annots = page_obj.get("/Annots") if hasattr(page_obj, "get") else None
            if annots:
                # annots can be an array of indirect references
                for annot in annots:
                    annot_obj = (
                        annot.get_object() if hasattr(annot, "get_object") else annot
                    )
                    if not annot_obj:
                        continue
                    action = annot_obj.get("/A")
                    if action:
                        action_obj = (
                            action.get_object()
                            if hasattr(action, "get_object")
                            else action
                        )
                        action_type = action_obj.get("/S")
                        if action_type in ("/JavaScript", "/JS", "/Launch"):
                            raise DocumentValidationError(
                                "Annotation contains JavaScript or Launch actions.",
                                "unsupported_pdf_feature",
                            )
    except DocumentValidationError:
        raise
    except Exception as e:
        raise DocumentValidationError(
            f"Safety scan failed: {str(e)}",
            "malformed_pdf",
        ) from e
