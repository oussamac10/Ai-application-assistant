from typing import Any

from app.core.config import settings
from app.documents.decryption import open_pdf
from app.documents.errors import DocumentValidationError


class PDFAnalyzer:
    def __init__(self, sample_limit: int = settings.DOCUMENT_TEXT_SAMPLE_LIMIT):
        self.sample_limit = sample_limit

    def analyze_document(self, filepath: str) -> dict[str, Any]:
        """Performs deterministic structural analysis on the PDF file."""
        try:
            # Permissions-encrypted forms open with an empty password; a
            # genuinely locked one is refused here as it is at upload.
            reader = open_pdf(filepath)
            page_count = len(reader.pages)
            if page_count == 0:
                raise DocumentValidationError(
                    "PDF contains zero pages.", "malformed_pdf"
                )

            pages_analysis: list[dict[str, Any]] = []
            total_char_count = 0
            has_any_acroform = False
            has_any_native_text = False
            has_any_images = False
            all_pages_scanned = True

            # Check document-level AcroForm
            catalog = reader.trailer.get("/Root")
            if catalog:
                catalog_obj = (
                    catalog.get_object() if hasattr(catalog, "get_object") else catalog
                )
                if "/AcroForm" in catalog_obj:
                    has_any_acroform = True

            # Extract fields list from document-level if available
            acroform_fields_list: list[dict[str, Any]] = []
            try:
                fields_dict = reader.get_fields()
                if fields_dict:
                    has_any_acroform = True
                    for field_name, field_info in fields_dict.items():
                        field_type = field_info.get("/FT", "unknown")
                        # Field type map: /Tx = Text, /Btn = Button (Check/Radio), /Ch = Choice, /Sig = Signature
                        ft_str = "text"
                        if field_type == "/Btn":
                            # Check if checkbox or radio button
                            flags = field_info.get("/Ff", 0)
                            # Radio button flag is 1 << 14 (16384)
                            if flags & 16384:
                                ft_str = "radio"
                            else:
                                ft_str = "checkbox"
                        elif field_type == "/Ch":
                            ft_str = "choice"
                        elif field_type == "/Sig":
                            ft_str = "signature"
                        elif field_type == "/Tx":
                            ft_str = "text"

                        required = bool(
                            field_info.get("/Ff", 0) & 1
                        )  # Required flag is bit 1

                        acroform_fields_list.append(
                            {"name": field_name, "type": ft_str, "required": required}
                        )
            except Exception:
                pass

            for idx, page in enumerate(reader.pages):
                page_num = idx + 1
                mediabox = page.mediabox
                width = float(mediabox.width) if mediabox else 0.0
                height = float(mediabox.height) if mediabox else 0.0
                rotation = int(page.get("/Rotate", 0))

                # Character extraction
                text = ""
                try:
                    text = page.extract_text() or ""
                except Exception:
                    pass

                normalized_text = " ".join(text.split())
                char_count = len(normalized_text)
                total_char_count += char_count

                # Native text flag
                page_has_native_text = char_count >= 15
                if page_has_native_text:
                    has_any_native_text = True

                # Image extraction
                image_count = 0
                try:
                    image_count = len(page.images)
                except Exception:
                    # Fallback resource search
                    try:
                        resources = page.get("/Resources", {})
                        if resources:
                            resources_obj = (
                                resources.get_object()
                                if hasattr(resources, "get_object")
                                else resources
                            )
                            xobject = resources_obj.get("/XObject", {})
                            if xobject:
                                xobject_obj = (
                                    xobject.get_object()
                                    if hasattr(xobject, "get_object")
                                    else xobject
                                )
                                for obj_name in xobject_obj:
                                    obj = xobject_obj[obj_name].get_object()
                                    if obj.get("/Subtype") == "/Image":
                                        image_count += 1
                    except Exception:
                        pass

                if image_count > 0:
                    has_any_images = True

                # A page is probably scanned if it has images and very little native text
                page_has_large_image = image_count >= 1 and char_count < 100

                # AcroForm count on page level (count Widgets)
                page_acroform_count = 0
                try:
                    annots = page.get("/Annots")
                    if annots:
                        annots_obj = (
                            annots.get_object()
                            if hasattr(annots, "get_object")
                            else annots
                        )
                        for annot in annots_obj:
                            annot_obj = (
                                annot.get_object()
                                if hasattr(annot, "get_object")
                                else annot
                            )
                            if annot_obj and annot_obj.get("/Subtype") == "/Widget":
                                page_acroform_count += 1
                except Exception:
                    pass

                # If any page has native text and no dominant full page image, it is not completely scanned
                if page_has_native_text and not page_has_large_image:
                    all_pages_scanned = False

                pages_analysis.append(
                    {
                        "page_number": page_num,
                        "width": width,
                        "height": height,
                        "rotation": rotation,
                        "has_native_text": page_has_native_text,
                        "native_text_character_count": char_count,
                        "image_count": image_count,
                        "has_large_page_image": page_has_large_image,
                        "acroform_field_count": page_acroform_count,
                    }
                )

            # Check if any page-level widgets found, update global flag
            if any(p["acroform_field_count"] > 0 for p in pages_analysis):
                has_any_acroform = True

            # Classify document
            # scanned_pdf: little/no native text, contains images, no AcroForm fields
            # fillable_pdf: contains AcroForm fields
            # digital_pdf: meaningful native text, no dominant full-page scan images, no AcroForm
            # hybrid_pdf: contains both digital & scanned pages OR both text & dominant images
            # unknown_pdf: signals are inconclusive (e.g., page with no text and no images)

            is_probably_scanned = False

            if has_any_acroform:
                doc_type = "fillable_pdf"
            elif not has_any_native_text and has_any_images:
                doc_type = "scanned_pdf"
                is_probably_scanned = True
            elif has_any_native_text and not has_any_images:
                doc_type = "digital_pdf"
            elif has_any_native_text and has_any_images:
                if all_pages_scanned:
                    doc_type = "scanned_pdf"
                    is_probably_scanned = True
                else:
                    doc_type = "hybrid_pdf"
                    # If most pages are scanned, mark as probably scanned
                    scanned_pages = sum(
                        1 for p in pages_analysis if p["has_large_page_image"]
                    )
                    if scanned_pages >= page_count / 2:
                        is_probably_scanned = True
            else:
                doc_type = "unknown_pdf"

            return {
                "page_count": page_count,
                "document_type": doc_type,
                "has_native_text": has_any_native_text,
                "has_acroform": has_any_acroform,
                "has_embedded_images": has_any_images,
                "is_probably_scanned": is_probably_scanned,
                "pages": pages_analysis,
                "acroform_fields": acroform_fields_list,
            }
        except Exception as e:
            if isinstance(e, DocumentValidationError):
                raise
            raise DocumentValidationError(
                f"Failed to analyze PDF structure: {str(e)}", "document_analysis_failed"
            ) from e
