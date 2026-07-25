from pathlib import Path

from pypdf import PdfReader, PdfWriter

from app.pdf.schemas import PDFTemplateMapping


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
    ) -> PDFRenderResult:
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

        # Get file metadata
        file_size = output_path.stat().st_size
        page_count = len(reader.pages)

        return PDFRenderResult(
            page_count=page_count,
            file_size=file_size,
            output_path=output_path,
        )
