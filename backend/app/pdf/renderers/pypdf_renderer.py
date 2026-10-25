from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter

from app.pdf.font_support import draw_unicode_text_in_box, is_latin1_safe
from app.pdf.schemas import PDFTemplateMapping
from app.pdf.signature_render import (
    SIGNATURE_EXPORT_FAILED,
    SignatureBox,
    SignatureRenderError,
    render_signature,
)


class PDFRenderResult:
    def __init__(self, page_count: int, file_size: int, output_path: Path) -> None:
        self.page_count = page_count
        self.file_size = file_size
        self.output_path = output_path


class PypdfRenderer:
    def render(
        self,
        *,
        template_path: Path,
        output_path: Path,
        mapping: PDFTemplateMapping,
        values: dict[str, object],
        signatures: list[tuple[SignatureBox, Any]] | None = None,
    ) -> PDFRenderResult:
        """Fills AcroForm fields, then draws any signatures.

        Two passes because they are two different operations on the document:
        pypdf sets field values, and a signature is ink at coordinates. Running
        the drawing pass afterwards on the already-written file keeps every
        untouched page and unrelated field exactly as pypdf left them — nothing
        is rasterised and nothing unrelated is flattened.
        """
        reader = PdfReader(template_path)
        writer = PdfWriter()

        # Copy all pages and AcroForm form catalog to writer
        writer.append(reader)

        # Build raw dict mapping pdfFieldName to the string value
        field_values: dict[str, str] = {}
        for field_map in mapping.fields:
            val = values.get(field_map.field_key)
            if val is not None:
                field_values[field_map.pdf_field_name] = str(val)

        latin1_field_values = {
            k: v for k, v in field_values.items() if is_latin1_safe(v)
        }
        unicode_field_values = {
            k: v for k, v in field_values.items() if not is_latin1_safe(v)
        }

        # Update page form field values across all pages and set read-only
        if latin1_field_values:
            from pypdf.constants import CatalogDictionary, FieldFlag
            from pypdf.generic import DictionaryObject, NameObject

            # Guard against pypdf's _update_field_annotation crashing with
            # AttributeError when an AcroForm catalog lacks a /DR dictionary.
            if CatalogDictionary.ACRO_FORM in writer.root_object:
                acro_form = writer.root_object[CatalogDictionary.ACRO_FORM].get_object()
                if isinstance(acro_form, DictionaryObject) and "/DR" not in acro_form:
                    acro_form[NameObject("/DR")] = DictionaryObject(
                        {
                            NameObject("/Font"): DictionaryObject(
                                {
                                    NameObject("/Helv"): DictionaryObject(
                                        {
                                            NameObject("/Type"): NameObject("/Font"),
                                            NameObject("/Subtype"): NameObject(
                                                "/Type1"
                                            ),
                                            NameObject("/BaseFont"): NameObject(
                                                "/Helvetica"
                                            ),
                                        }
                                    )
                                }
                            )
                        }
                    )

            for page in writer.pages:
                writer.update_page_form_field_values(
                    page,
                    latin1_field_values,
                    flags=FieldFlag.READ_ONLY,
                )

        # Write output file safely
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            writer.write(f)

        if unicode_field_values:
            self._draw_unicode_widgets(output_path, unicode_field_values)

        if signatures:
            self._draw_signatures(output_path, signatures)

        # Get file metadata
        file_size = output_path.stat().st_size
        page_count = len(reader.pages)

        return PDFRenderResult(
            page_count=page_count,
            file_size=file_size,
            output_path=output_path,
        )

    @staticmethod
    def _draw_unicode_widgets(
        output_path: Path, unicode_field_values: dict[str, str]
    ) -> None:
        """Overlays non-WinAnsi Unicode AcroForm text fields (Arabic, Cyrillic,
        Turkish/Polish diacritics) using embedded Noto Sans / Noto Sans Arabic TTFs.
        """
        import fitz

        document = fitz.open(output_path)
        try:
            touched = False
            for page in document:
                for widget in list(page.widgets() or []):
                    name = getattr(widget, "field_name", None)
                    if not name or name not in unicode_field_values:
                        continue
                    rect = widget.rect
                    val = unicode_field_values[name]
                    try:
                        page.delete_widget(widget)
                    except Exception:
                        pass
                    draw_unicode_text_in_box(
                        page,
                        x=float(rect.x0),
                        y=float(rect.y0),
                        width=float(rect.width),
                        height=float(rect.height),
                        text=val,
                        multiline=float(rect.height) >= 36.0,
                    )
                    touched = True
            if touched:
                document.saveIncr()
        finally:
            document.close()

    @staticmethod
    def _draw_signatures(
        output_path: Path, signatures: list[tuple[SignatureBox, Any]]
    ) -> None:
        """Draws each signature onto the already-written document.

        Only the pages carrying a signature are touched; every other page is
        rewritten byte-for-byte by the incremental save. A `pending_manual_
        signature` never reaches here — the service does not include it — so
        its box is left exactly as the form's author drew it.
        """
        import fitz

        document = fitz.open(output_path)
        try:
            for box, payload in signatures:
                index = box.page_number - 1
                if not (0 <= index < document.page_count):
                    raise SignatureRenderError(
                        SIGNATURE_EXPORT_FAILED,
                        "The signature page is outside the document.",
                    )
                render_signature(document[index], box, payload)
            document.saveIncr()
        finally:
            # Always closed, so a failed export leaves no handle on a file the
            # caller is about to delete.
            document.close()
