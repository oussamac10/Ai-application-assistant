from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter

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
        field_values = {}
        for field_map in mapping.fields:
            val = values.get(field_map.field_key)
            if val is not None:
                field_values[field_map.pdf_field_name] = str(val)

        # Update page form field values and set read-only/flatten
        if field_values:
            from pypdf.constants import FieldFlag

            writer.update_page_form_field_values(
                writer.pages[0],
                field_values,
                flags=FieldFlag.READ_ONLY,
            )

        # Write output file safely
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "wb") as f:
            writer.write(f)

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
