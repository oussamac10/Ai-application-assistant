import logging
import os
from typing import Any, cast

import pypdf
from pypdf.generic import NullObject

from app.documents.decryption import open_pdf
from app.documents.errors import DocumentValidationError

logger = logging.getLogger(__name__)


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
        # An encryption dictionary is not a lock. Most government forms are
        # encrypted for *permissions* and open with an empty password; only a
        # file that genuinely refuses one is rejected. See decryption.py.
        reader = open_pdf(filepath)

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
            "This PDF requires a password.",
            "pdf_password_required",
        ) from e
    except DocumentValidationError:
        raise
    except Exception as e:
        # Never echo the parser's message: pypdf exceptions can carry object
        # contents, and document contents are private.
        raise DocumentValidationError(
            "Malformed PDF or corrupted structure.",
            "malformed_pdf",
        ) from e


def _deref(obj: Any) -> Any:
    if obj is None:
        return None
    val = obj.get_object() if hasattr(obj, "get_object") else obj
    if isinstance(val, NullObject):
        return None
    return val


def _has_active_pdf_content(reader: Any) -> bool:
    """Returns True if the PDF contains non-empty JavaScript, OpenAction,
    Additional Actions, Launch actions, or embedded files that must be
    neutralized before processing.
    """
    catalog_obj = _deref(reader.trailer.get("/Root"))
    if not catalog_obj or not hasattr(catalog_obj, "get"):
        return False

    for key in ("/JavaScript", "/JS", "/OpenAction", "/AA"):
        if _deref(catalog_obj.get(key)) is not None:
            return True

    names_obj = _deref(catalog_obj.get("/Names"))
    if names_obj and hasattr(names_obj, "get"):
        if (
            _deref(names_obj.get("/EmbeddedFiles")) is not None
            or _deref(names_obj.get("/JavaScript")) is not None
        ):
            return True

    for page in reader.pages:
        page_obj = _deref(page)
        if page_obj is None:
            continue
        if _deref(cast(Any, page_obj).get("/AA")) is not None:
            return True

        annots_obj = (
            _deref(page_obj.get("/Annots")) if hasattr(page_obj, "get") else None
        )
        if isinstance(annots_obj, list):
            for annot in annots_obj:
                annot_obj = _deref(annot)
                if not annot_obj or not hasattr(annot_obj, "get"):
                    continue
                if _deref(annot_obj.get("/AA")) is not None:
                    return True
                action_obj = _deref(annot_obj.get("/A"))
                if action_obj and hasattr(action_obj, "get"):
                    action_type = action_obj.get("/S")
                    if action_type in ("/JavaScript", "/JS", "/Launch"):
                        js_payload = _deref(action_obj.get("/JS"))
                        if action_type == "/Launch" or (
                            js_payload is not None and str(js_payload).strip() != ""
                        ):
                            return True

    return False


def _sanitize_pdf_active_content(filepath: str) -> None:
    """Strips embedded JavaScript, OpenAction, Additional Actions (/AA), Launch
    actions, and embedded file attachments in place using PyMuPDF while keeping
    all visual pages, text, and fillable AcroForm widgets intact.

    Many official municipal and government PDF forms (such as German
    *Wohnungsgeberbestätigung*, *Kindergeld*, and *Wohngeld* forms) include
    "Drucken" (Print) and "Alle Angaben löschen" (Reset) buttons or field-level
    formatting scripts (`/AA`). Neutralizing active triggers in place allows
    citizens to upload and complete real government forms safely.
    """
    import fitz

    tmp_filepath = f"{filepath}.sanitized.pdf"
    doc = fitz.open(filepath)
    try:
        if doc.is_encrypted:
            doc.authenticate("")

        doc.scrub(
            attached_files=True,
            clean_pages=False,
            embedded_files=True,
            hidden_text=False,
            javascript=True,
            metadata=False,
            redactions=False,
            redact_images=0,
            remove_links=False,
            reset_fields=False,
            reset_responses=False,
            thumbnails=False,
            xml_metadata=False,
        )

        cat_xref = doc.pdf_catalog()
        if cat_xref > 0:
            for cat_key in (
                "OpenAction",
                "AA",
                "JavaScript",
                "JS",
                "Names/JavaScript",
                "Names/EmbeddedFiles",
            ):
                try:
                    doc.xref_set_key(cat_xref, cat_key, "null")
                except Exception:
                    continue

        # Strip any remaining /OpenAction, /AA, or /JavaScript / /Launch action
        # dictionaries across indirect objects so no viewer or parser ever
        # encounters active triggers.
        for xref in range(1, doc.xref_length()):
            try:
                if not doc.xref_is_dict(xref):
                    continue
                for key in (
                    "OpenAction",
                    "AA",
                    "JavaScript",
                    "JS",
                    "EmbeddedFiles",
                ):
                    kind, _val = doc.xref_get_key(xref, key)
                    if kind != "null":
                        doc.xref_set_key(xref, key, "null")
                action_s_kind, action_s_val = doc.xref_get_key(xref, "S")
                if action_s_kind == "name" and action_s_val in (
                    "/JavaScript",
                    "/JS",
                    "/Launch",
                ):
                    doc.xref_set_key(xref, "S", "null")
                    doc.xref_set_key(xref, "JS", "null")
                    doc.xref_set_key(xref, "F", "null")
                sub_s_kind, sub_s_val = doc.xref_get_key(xref, "A/S")
                if sub_s_kind == "name" and sub_s_val in (
                    "/JavaScript",
                    "/JS",
                    "/Launch",
                ):
                    doc.xref_set_key(xref, "A", "null")
            except Exception:
                continue

        doc.save(tmp_filepath, garbage=2, deflate=True)
    finally:
        doc.close()

    os.replace(tmp_filepath, filepath)
    logger.info(
        "Sanitized active PDF content (JavaScript/actions) in uploaded document."
    )


def validate_pdf_safety(filepath: str) -> None:
    """Scans the PDF catalog and pages for active content and neutralizes any
    embedded JavaScript, automatic actions, or attachments in place.
    """
    try:
        reader = open_pdf(filepath)
        if _has_active_pdf_content(reader):
            _sanitize_pdf_active_content(filepath)
    except DocumentValidationError:
        raise
    except Exception as e:
        raise DocumentValidationError(
            "Safety scan failed.",
            "malformed_pdf",
        ) from e
