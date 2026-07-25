import json
from pathlib import Path

from pydantic import ValidationError

from app.pdf.schemas import PDFTemplateMapping


class PDFMappingError(Exception):
    pass


class PDFTemplateRegistry:
    def __init__(self, fixtures_dir: Path | None = None) -> None:
        if fixtures_dir is None:
            # Fallback to root fixtures/pdf
            self.fixtures_dir = Path(__file__).resolve().parents[3] / "fixtures" / "pdf"
        else:
            self.fixtures_dir = fixtures_dir

    def get_template_path(self, template_key: str) -> Path:
        path = self.fixtures_dir / f"{template_key}.pdf"
        if not path.is_file():
            raise PDFMappingError(
                f"PDF template file for '{template_key}' not found at {path}"
            )
        return path

    def get_mapping_path(self, template_key: str) -> Path:
        path = self.fixtures_dir / f"{template_key}.mapping.json"
        if not path.is_file():
            raise PDFMappingError(
                f"PDF mapping file for '{template_key}' not found at {path}"
            )
        return path


class PDFMappingLoader:
    def __init__(self, registry: PDFTemplateRegistry) -> None:
        self.registry = registry

    def load_mapping(self, template_key: str) -> PDFTemplateMapping:
        path = self.registry.get_mapping_path(template_key)
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            raise PDFMappingError(f"Failed to read/parse mapping file: {str(e)}") from e

        try:
            mapping = PDFTemplateMapping.model_validate(data)
        except ValidationError as e:
            raise PDFMappingError(f"Invalid PDF mapping configuration: {str(e)}") from e

        # Validate unique field keys and unique PDF field names
        field_keys = set()
        pdf_field_names = set()
        for field in mapping.fields:
            if field.field_key in field_keys:
                raise PDFMappingError(f"Duplicate mapping field key: {field.field_key}")
            if field.pdf_field_name in pdf_field_names:
                raise PDFMappingError(
                    f"Duplicate mapping PDF field name: {field.pdf_field_name}"
                )
            field_keys.add(field.field_key)
            pdf_field_names.add(field.pdf_field_name)

        return mapping
