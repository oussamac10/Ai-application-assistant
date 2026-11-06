from pydantic import BaseModel, Field

from app.organizations.schemas import PublicOrganizationSummary


class PublicFormDetail(BaseModel):
    id: str
    key: str
    name: str
    description: str | None = None
    category: str = "general"
    submission_method: str = "print_and_sign"
    instructions: str | None = None
    required_documents: list[str] = Field(default_factory=list)
    active_version_id: str
    version_number: int = 1
    source_language: str = "de"
    supported_output_languages: list[str] = Field(default_factory=list)
    fields_count: int = 0
    has_pdf: bool = False
    organization: PublicOrganizationSummary | None = None
    share_url: str
    qr_svg_url: str
    qr_png_url: str
    counter_poster_pdf_url: str
