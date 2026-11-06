from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.forms.models import FormTemplate, FormVersion
from app.forms.public_qr_service import (
    generate_counter_poster_pdf,
    generate_qr_png,
    generate_qr_svg,
)
from app.forms.public_schemas import PublicFormDetail
from app.organizations.models import Organization
from app.organizations.schemas import PublicOrganizationSummary
from app.organizations.services import OrganizationService


class PublicFormService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def resolve_form_and_version(
        self, identifier: str
    ) -> tuple[FormTemplate, FormVersion, Organization | None]:
        """Resolves a published form and its active version by key, id, or org_slug/form_key."""
        identifier = identifier.strip()
        org: Organization | None = None

        if "/" in identifier:
            parts = identifier.split("/", 1)
            org_slug, form_key = parts[0].strip(), parts[1].strip()
            org_stmt = select(Organization).where(Organization.slug == org_slug)
            org = self.db.scalars(org_stmt).first()
            if not org:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Organization '{org_slug}' was not found.",
                )
            stmt = (
                select(FormTemplate, FormVersion)
                .join(FormVersion, FormVersion.form_template_id == FormTemplate.id)
                .where(
                    FormTemplate.organization_id == org.id,
                    FormTemplate.key == form_key,
                    FormVersion.status == "published",
                )
                .order_by(FormVersion.version_number.desc())
            )
        else:
            stmt = (
                select(FormTemplate, FormVersion)
                .join(FormVersion, FormVersion.form_template_id == FormTemplate.id)
                .where(
                    or_(
                        FormTemplate.key == identifier,
                        FormTemplate.id == identifier,
                    ),
                    FormVersion.status == "published",
                )
                .order_by(FormVersion.version_number.desc())
            )

        row = self.db.execute(stmt).first()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Published form '{identifier}' was not found.",
            )

        template, version = row
        if not org and template.organization_id:
            org_stmt = select(Organization).where(
                Organization.id == template.organization_id
            )
            org = self.db.scalars(org_stmt).first()

        return template, version, org

    def get_public_form_detail(
        self, identifier: str, frontend_origin: str = ""
    ) -> PublicFormDetail:
        template, version, org = self.resolve_form_and_version(identifier)
        fields_count = len(version.fields) if version.fields else 0

        org_summary: PublicOrganizationSummary | None = None
        if org:
            org_summary = PublicOrganizationSummary(
                id=org.id,
                name=org.name,
                slug=org.slug,
                organization_type=org.organization_type,
                verification_status=org.verification_status,
                is_verified_government=org.is_verified_government,
                description=org.description,
                office_address=org.office_address,
                official_website_url=org.official_website_url,
                has_logo=bool(org.logo_storage_path),
                published_forms_count=0,
                supported_languages=org.supported_languages or ["de", "en"],
            )

        share_path = f"/f/{template.key}"
        share_url = f"{frontend_origin}{share_path}" if frontend_origin else share_path

        return PublicFormDetail(
            id=template.id,
            key=template.key,
            name=template.name,
            description=template.description,
            category=template.category,
            submission_method=template.submission_method,
            instructions=template.instructions,
            required_documents=template.required_documents or [],
            active_version_id=version.id,
            version_number=version.version_number,
            source_language=version.source_language,
            supported_output_languages=version.supported_output_languages
            or ["en", "de"],
            fields_count=fields_count,
            has_pdf=bool(version.source_pdf_storage_path or version.pdf_template_key),
            organization=org_summary,
            share_url=share_url,
            qr_svg_url=f"/api/public/forms/{template.key}/qr?format=svg",
            qr_png_url=f"/api/public/forms/{template.key}/qr?format=png",
            counter_poster_pdf_url=f"/api/public/forms/{template.key}/counter-poster.pdf",
        )

    def get_qr_bytes(
        self,
        identifier: str,
        fmt: str = "png",
        frontend_origin: str = "http://localhost:3000",
    ) -> tuple[bytes, str]:
        template, _, _ = self.resolve_form_and_version(identifier)
        target_url = f"{frontend_origin.rstrip('/')}/f/{template.key}"

        if fmt.lower() == "svg":
            svg_str = generate_qr_svg(target_url, size=300)
            return svg_str.encode("utf-8"), "image/svg+xml"
        else:
            png_bytes = generate_qr_png(target_url, size=300)
            return png_bytes, "image/png"

    def get_counter_poster_bytes(
        self, identifier: str, frontend_origin: str = "http://localhost:3000"
    ) -> tuple[bytes, str]:
        template, _, org = self.resolve_form_and_version(identifier)
        target_url = f"{frontend_origin.rstrip('/')}/f/{template.key}"

        org_name = org.name if org else None
        is_gov = org.is_verified_government if org else False
        logo_bytes: bytes | None = None

        if org and org.logo_storage_path:
            try:
                org_svc = OrganizationService(self.db)
                raw_bytes, _ = org_svc.get_branding_image(org.id, "logo")
                logo_bytes = raw_bytes
            except Exception:
                logo_bytes = None

        pdf_bytes = generate_counter_poster_pdf(
            form_name=template.name,
            target_url=target_url,
            org_name=org_name,
            org_logo_bytes=logo_bytes,
            is_verified_government=is_gov,
            instructions=template.instructions,
        )
        filename = f"counter-poster-{template.key}.pdf"
        return pdf_bytes, filename
