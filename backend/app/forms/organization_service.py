"""Organization Form Management & Schema Review Service (Phase G2).

Empowers municipal and agency staff (Owners, Admins, Form Editors) to:
- Upload official blank PDF forms
- Extract native AcroForm widgets & page text geometry
- Review, rename, reorder, and configure form fields in the Review Studio
- Manage form metadata (category, submission method, instructions, required documents)
- Approve and publish forms to the organization workspace catalog
"""

from __future__ import annotations

import logging
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.auth.models import User
from app.forms.learning_service import FormPatternLearningService
from app.forms.models import (
    FormField,
    FormFieldOption,
    FormFieldOptionTranslation,
    FormFieldTranslation,
    FormTemplate,
    FormVersion,
)
from app.forms.pdf_field_extractor import (
    extract_fields_from_pdf_bytes,
    get_pdf_page_dimensions,
    insert_extracted_fields,
    render_pdf_page_png,
    slugify,
)
from app.forms.schemas import (
    CombineChoiceFieldsRequest,
    FieldCreate,
    FieldResponse,
    FieldUpdate,
    FormReviewDetailResponse,
    FormReviewUpdateRequest,
    GroupTableRowRequest,
    OptionSchema,
    OptionTranslationSchema,
    OrganizationFormSummary,
    SyncTableColumnsRequest,
    TranslationSchema,
)
from app.organizations.models import OrganizationCase
from app.organizations.repositories import CategoryRepository, OrganizationRepository
from app.pdf.models import FormExport
from app.sessions.models import FormSession
from app.storage.factory import get_storage_provider

logger = logging.getLogger(__name__)


class OrganizationFormService:
    def __init__(self, db: Session):
        self.db = db
        self.org_repo = OrganizationRepository(db)
        self.storage = get_storage_provider()

    def _require_org_editor(self, user: User) -> tuple[Any, Any]:
        """Ensures user belongs to an organization with editor permissions."""
        from app.organizations.services import OrganizationService

        org, membership = OrganizationService(self.db).ensure_default_organization(user)
        if membership.role not in ("owner", "admin", "form_editor"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners, administrators, and form editors can manage templates.",
            )
        return org, membership

    def _require_org_viewer(self, user: User) -> tuple[Any, Any]:
        """Ensures user belongs to an organization with at least viewer permissions."""
        from app.organizations.services import OrganizationService

        org, membership = OrganizationService(self.db).ensure_default_organization(user)
        return org, membership

    def _get_form_template_and_version(
        self, org_id: str, template_id: str
    ) -> tuple[FormTemplate, FormVersion]:
        """Helper to fetch a form template and its latest version scoped to an organization."""
        template = (
            self.db.query(FormTemplate)
            .filter(
                FormTemplate.id == template_id, FormTemplate.organization_id == org_id
            )
            .first()
        )
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Form template not found."
            )

        latest_version = (
            self.db.query(FormVersion)
            .filter(FormVersion.form_template_id == template.id)
            .order_by(FormVersion.version_number.desc())
            .first()
        )
        if not latest_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Form version not found."
            )

        return template, latest_version

    def list_organization_forms(self, user: User) -> list[OrganizationFormSummary]:
        org, _ = self._require_org_viewer(user)

        templates = (
            self.db.query(FormTemplate)
            .options(joinedload(FormTemplate.category_rel))
            .filter(FormTemplate.organization_id == org.id)
            .order_by(FormTemplate.updated_at.desc())
            .all()
        )

        summaries: list[OrganizationFormSummary] = []
        for tmpl in templates:
            # Get latest version
            latest_version = (
                self.db.query(FormVersion)
                .filter(FormVersion.form_template_id == tmpl.id)
                .order_by(FormVersion.version_number.desc())
                .first()
            )
            fields_count = (
                self.db.query(func.count(FormField.id))
                .filter(FormField.form_version_id == latest_version.id)
                .scalar()
                if latest_version
                else 0
            )

            cat_rel = tmpl.category_rel
            summaries.append(
                OrganizationFormSummary(
                    id=tmpl.id,
                    key=tmpl.key,
                    name=tmpl.name,
                    description=tmpl.description,
                    category=tmpl.category,
                    category_id=tmpl.category_id,
                    category_name=cat_rel.name if cat_rel else None,
                    category_slug=cat_rel.slug if cat_rel else None,
                    category_icon=cat_rel.icon if cat_rel else None,
                    submission_method=tmpl.submission_method,
                    instructions=tmpl.instructions,
                    required_documents=tmpl.required_documents or [],
                    active_version_id=latest_version.id if latest_version else None,
                    version_number=latest_version.version_number
                    if latest_version
                    else 1,
                    status=latest_version.status if latest_version else "needs_review",
                    fields_count=fields_count,
                    source_pdf_storage_path=latest_version.source_pdf_storage_path
                    if latest_version
                    else None,
                    has_pdf=bool(
                        latest_version and latest_version.source_pdf_storage_path
                    ),
                    created_at=tmpl.created_at,
                    updated_at=tmpl.updated_at,
                )
            )

        return summaries

    def upload_and_ingest_form(
        self,
        user: User,
        pdf_bytes: bytes,
        filename: str,
        name: str,
        category: str = "general",
        category_id: str | None = None,
        submission_method: str = "print_and_sign",
        instructions: str | None = None,
        required_documents: list[str] | None = None,
        auto_extract: bool = False,
    ) -> FormReviewDetailResponse:
        org, _ = self._require_org_editor(user)

        # 1. Enforce strict PDF document contract (magic bytes + filename)
        if not pdf_bytes.startswith(b"%PDF-"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file must be a valid PDF document.",
            )

        doc_uuid = str(uuid.uuid4())
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = Path(tmp.name)

        try:
            stored_filename = f"org-form-{doc_uuid[:8]}.pdf"
            storage_path = self.storage.save_file(
                "documents",
                stored_filename,
                tmp_path,
                content_type="application/pdf",
            )
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

        # 3. Create FormTemplate
        clean_name = (name.strip() or "Unbenanntes Formular")[:255]
        base_slug = (slugify(clean_name) or "form")[:91].rstrip("-") or "form"
        unique_key = f"{base_slug}-{doc_uuid[:8]}"

        assigned_cat_id = None
        if category_id:
            from app.organizations.repositories import CategoryRepository

            cat_repo = CategoryRepository(self.db)
            cat = cat_repo.get_by_id(org.id, category_id)
            if cat:
                assigned_cat_id = cat.id
                category = cat.slug

        template = FormTemplate(
            organization_id=org.id,
            category_id=assigned_cat_id,
            key=unique_key,
            name=clean_name,
            description=None,
            category=category.strip() or "general",
            submission_method=submission_method.strip() or "print_and_sign",
            instructions=instructions.strip() if instructions else None,
            required_documents=required_documents or [],
        )
        self.db.add(template)
        self.db.flush()

        # 4. Create FormVersion (status: needs_review)
        version = FormVersion(
            form_template_id=template.id,
            version_number=1,
            status="needs_review",
            source_language="de",
            supported_output_languages=["de"],
            origin="organization_template",
            source_pdf_storage_path=storage_path,
        )
        self.db.add(version)
        self.db.flush()

        # 5. Extract fields from PDF only if explicitly requested
        if auto_extract:
            extracted_fields = self._extract_fields_from_pdf_bytes(pdf_bytes)
            extracted_fields = FormPatternLearningService(
                self.db
            ).enrich_extracted_fields(
                extracted_fields,
                source_language=version.source_language or "de",
                organization_id=org.id,
            )
            self._insert_extracted_fields(
                version.id, extracted_fields, version.source_language or "de"
            )

        self.db.commit()
        return self.get_form_review(user, template.id)

    def _extract_fields_from_pdf_bytes(self, pdf_bytes: bytes) -> list[dict[str, Any]]:
        """Extracts candidate fields from interactive AcroForms or layout text."""
        return extract_fields_from_pdf_bytes(pdf_bytes)

    def _insert_extracted_fields(
        self,
        version_id: str,
        extracted_fields: list[dict[str, Any]],
        source_language: str = "de",
    ) -> None:
        """Inserts extracted fields into database with unique keys and source translation."""
        insert_extracted_fields(self.db, version_id, extracted_fields, source_language)

    def auto_detect_fields(
        self, user: User, template_id: str
    ) -> FormReviewDetailResponse:
        """On-demand scan and extraction of fields from the attached form document."""
        org, _ = self._require_org_editor(user)
        template, latest_version = self._get_form_template_and_version(
            org.id, template_id
        )

        if not latest_version.source_pdf_storage_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No source PDF attached to this form version.",
            )

        pdf_bytes = self.storage.get_bytes(latest_version.source_pdf_storage_path)
        extracted_fields = self._extract_fields_from_pdf_bytes(pdf_bytes)
        src_lang = latest_version.source_language or "de"
        extracted_fields = FormPatternLearningService(self.db).enrich_extracted_fields(
            extracted_fields,
            source_language=src_lang,
            organization_id=org.id,
        )

        # Clear existing unverified fields so re-scanning replaces rather than duplicates with _2 suffixes
        existing_fields = (
            self.db.query(FormField)
            .filter(FormField.form_version_id == latest_version.id)
            .all()
        )
        for ef in existing_fields:
            self.db.delete(ef)
        self.db.flush()

        self._insert_extracted_fields(
            latest_version.id,
            extracted_fields,
            src_lang,
        )
        self.db.commit()

        return self.get_form_review(user, template_id)

    def get_form_review(self, user: User, template_id: str) -> FormReviewDetailResponse:
        org, _ = self._require_org_viewer(user)

        template = (
            self.db.query(FormTemplate)
            .filter(
                FormTemplate.id == template_id, FormTemplate.organization_id == org.id
            )
            .first()
        )
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Form template not found."
            )

        latest_version = (
            self.db.query(FormVersion)
            .filter(FormVersion.form_template_id == template.id)
            .order_by(FormVersion.version_number.desc())
            .options(
                joinedload(FormVersion.fields).joinedload(FormField.translations),
                joinedload(FormVersion.fields).joinedload(FormField.options),
            )
            .first()
        )
        if not latest_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Form version not found."
            )

        # Map fields to FieldResponse
        fields_resp: list[FieldResponse] = []
        for field in sorted(latest_version.fields, key=lambda f: f.position):
            translations = [
                TranslationSchema(
                    language=t.language,
                    label=t.label,
                    help_text=t.help_text,
                    placeholder=t.placeholder,
                )
                for t in field.translations
            ]
            options = [
                OptionSchema(
                    id=opt.id,
                    value=opt.value,
                    position=opt.position,
                    translations=[
                        OptionTranslationSchema(language=ot.language, label=ot.label)
                        for ot in opt.translations
                    ],
                )
                for opt in sorted(field.options, key=lambda o: o.position)
            ]
            fields_resp.append(
                FieldResponse(
                    id=field.id,
                    key=field.key,
                    field_type=field.field_type,
                    required=field.required,
                    requiredness=field.requiredness,
                    position=field.position,
                    configuration=field.configuration or {},
                    question_key=field.question_key,
                    translations=translations,
                    options=options,
                )
            )

        page_count = 1
        page_dimensions: list[dict[str, Any]] = []
        if latest_version.source_pdf_storage_path:
            try:
                pdf_bytes = self.storage.get_bytes(
                    latest_version.source_pdf_storage_path
                )
                page_count, page_dimensions = get_pdf_page_dimensions(pdf_bytes)
            except Exception as e:
                logger.warning("Could not read PDF page dimensions: %s", e)

        return FormReviewDetailResponse(
            template_id=template.id,
            version_id=latest_version.id,
            key=template.key,
            name=template.name,
            description=template.description,
            category=template.category,
            category_id=template.category_id,
            submission_method=template.submission_method,
            instructions=template.instructions,
            required_documents=template.required_documents or [],
            status=latest_version.status,
            version_number=latest_version.version_number,
            source_language=latest_version.source_language,
            source_pdf_storage_path=latest_version.source_pdf_storage_path,
            review_notes=latest_version.review_notes,
            page_count=page_count,
            page_dimensions=page_dimensions,
            fields=fields_resp,
        )

    def update_form_review(
        self, user: User, template_id: str, req: FormReviewUpdateRequest
    ) -> FormReviewDetailResponse:
        org, _ = self._require_org_editor(user)
        template, latest_version = self._get_form_template_and_version(
            org.id, template_id
        )

        if req.name is not None and req.name.strip():
            template.name = req.name.strip()
        if req.description is not None:
            template.description = req.description.strip() or None
        if req.category is not None and req.category.strip():
            template.category = req.category.strip()
        if req.category_id is not None:
            if not req.category_id or req.category_id.lower() in ("none", "null", ""):
                template.category_id = None
            else:
                from app.organizations.repositories import CategoryRepository

                cat_repo = CategoryRepository(self.db)
                cat = cat_repo.get_by_id(org.id, req.category_id)
                if cat:
                    template.category_id = cat.id
                    if not req.category:
                        template.category = cat.slug
        if req.submission_method is not None and req.submission_method.strip():
            template.submission_method = req.submission_method.strip()
        if req.instructions is not None:
            template.instructions = req.instructions.strip() or None
        if req.required_documents is not None:
            template.required_documents = req.required_documents
        if req.review_notes is not None:
            latest_version.review_notes = req.review_notes.strip() or None

        self.db.commit()
        return self.get_form_review(user, template_id)

    def update_form_category(
        self, user: User, template_id: str, category_id: str | None
    ) -> OrganizationFormSummary:
        org, _ = self._require_org_editor(user)

        template = (
            self.db.query(FormTemplate)
            .filter(
                FormTemplate.id == template_id,
                FormTemplate.organization_id == org.id,
            )
            .first()
        )
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Form template not found."
            )

        latest_version = (
            self.db.query(FormVersion)
            .filter(FormVersion.form_template_id == template.id)
            .order_by(FormVersion.version_number.desc())
            .first()
        )

        if (
            category_id
            and category_id.strip()
            and category_id.lower() not in ("none", "null")
        ):
            cat_repo = CategoryRepository(self.db)
            cat = cat_repo.get_by_id(org.id, category_id.strip())
            if not cat:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Category '{category_id}' not found in this organization.",
                )
            template.category_id = cat.id
            template.category = cat.name
        else:
            template.category_id = None
            template.category = "general"

        template.updated_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(template)

        fields_count = (
            self.db.query(func.count(FormField.id))
            .filter(FormField.form_version_id == latest_version.id)
            .scalar()
            if latest_version
            else 0
        )

        cat_rel = template.category_rel
        return OrganizationFormSummary(
            id=template.id,
            key=template.key,
            name=template.name,
            description=template.description,
            category=template.category,
            category_id=template.category_id,
            category_name=cat_rel.name if cat_rel else None,
            category_slug=cat_rel.slug if cat_rel else None,
            category_icon=cat_rel.icon if cat_rel else None,
            submission_method=template.submission_method,
            instructions=template.instructions,
            required_documents=template.required_documents or [],
            active_version_id=latest_version.id if latest_version else None,
            version_number=latest_version.version_number if latest_version else 1,
            status=latest_version.status if latest_version else "needs_review",
            fields_count=fields_count,
            source_pdf_storage_path=latest_version.source_pdf_storage_path
            if latest_version
            else None,
            has_pdf=bool(latest_version and latest_version.source_pdf_storage_path),
            created_at=template.created_at,
            updated_at=template.updated_at,
        )

    def auto_categorize_forms(self, user: User) -> dict[str, Any]:
        org, _ = self._require_org_editor(user)

        cat_repo = CategoryRepository(self.db)
        existing_cats = cat_repo.list_by_organization(org.id)
        if not existing_cats:
            return {
                "categorized_count": 0,
                "total_forms": 0,
                "details": [],
            }

        slug_to_cat = {c.slug: c for c in existing_cats}

        keywords_map: dict[str, list[str]] = {
            "housing-residence": [
                "wohnung",
                "anmeldung",
                "meldebehörde",
                "miete",
                "umzug",
                "wohnsitz",
                "residence",
                "housing",
                "tenant",
                "rental",
                "rundfunk",
            ],
            "family-children": [
                "kinder",
                "kind",
                "eltern",
                "geburt",
                "ehe",
                "familie",
                "kita",
                "child",
                "parent",
                "birth",
                "marriage",
            ],
            "immigration-residence": [
                "aufenthalt",
                "ausländer",
                "visum",
                "visa",
                "schengen",
                "einbürgerung",
                "pass",
                "asyl",
                "immigration",
                "foreign",
                "citizenship",
            ],
            "work-business": [
                "arbeit",
                "gewerbe",
                "beruf",
                "job",
                "steuer",
                "sepa",
                "bank",
                "business",
                "employment",
                "tax",
            ],
            "mobility-vehicles": [
                "kfz",
                "auto",
                "fahrzeug",
                "führerschein",
                "park",
                "verkehr",
                "vehicle",
                "car",
                "driver",
                "traffic",
            ],
            "social-health": [
                "sozial",
                "gesundheit",
                "kranken",
                "wohngeld",
                "pflege",
                "hilfe",
                "social",
                "health",
                "insurance",
                "welfare",
            ],
        }

        templates = (
            self.db.query(FormTemplate)
            .filter(FormTemplate.organization_id == org.id)
            .all()
        )

        categorized_count = 0
        details: list[dict[str, Any]] = []

        for tmpl in templates:
            target_slug = None
            text_to_check = f"{tmpl.name} {tmpl.key} {tmpl.description or ''}".lower()

            for cat_slug, keywords in keywords_map.items():
                if any(kw in text_to_check for kw in keywords):
                    target_slug = cat_slug
                    break

            if target_slug and target_slug in slug_to_cat:
                matched_cat = slug_to_cat[target_slug]
                if tmpl.category_id != matched_cat.id:
                    tmpl.category_id = matched_cat.id
                    tmpl.category = matched_cat.name
                    tmpl.updated_at = datetime.now(UTC)
                    categorized_count += 1
                    details.append(
                        {
                            "form_id": tmpl.id,
                            "form_name": tmpl.name,
                            "category": matched_cat.name,
                        }
                    )

        self.db.commit()
        return {
            "categorized_count": categorized_count,
            "total_forms": len(templates),
            "details": details,
        }

    def update_field(
        self, user: User, template_id: str, field_id: str, req: FieldUpdate
    ) -> FieldResponse:
        org, _ = self._require_org_editor(user)

        field = (
            self.db.query(FormField)
            .filter(FormField.id == field_id)
            .options(joinedload(FormField.translations), joinedload(FormField.options))
            .first()
        )
        if not field:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Field not found."
            )

        if req.key is not None and req.key.strip():
            new_key = slugify(req.key)
            existing = (
                self.db.query(FormField)
                .filter(
                    FormField.form_version_id == field.form_version_id,
                    FormField.key == new_key,
                    FormField.id != field.id,
                )
                .first()
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Field key '{new_key}' is already used by another field in this form.",
                )
            field.key = new_key
        if req.field_type is not None:
            field.field_type = req.field_type
        if req.requiredness is not None:
            field.requiredness = req.requiredness
            field.required = req.requiredness == "required"
        elif req.required is not None:
            field.required = req.required
            field.requiredness = "required" if req.required else "optional"
        if req.position is not None:
            field.position = req.position
        if req.question_key is not None:
            field.question_key = req.question_key.strip() or None
        if req.configuration is not None:
            field.configuration = req.configuration

        # Update translation if provided
        if req.translations:
            for t_in in req.translations:
                existing_t = next(
                    (t for t in field.translations if t.language == t_in.language), None
                )
                if existing_t:
                    existing_t.label = t_in.label
                    existing_t.help_text = t_in.help_text
                    existing_t.placeholder = t_in.placeholder
                else:
                    new_t = FormFieldTranslation(
                        form_field_id=field.id,
                        language=t_in.language,
                        label=t_in.label,
                        help_text=t_in.help_text,
                        placeholder=t_in.placeholder,
                    )
                    self.db.add(new_t)

        field_version = self.db.get(FormVersion, field.form_version_id)
        src_lang = (field_version.source_language if field_version else None) or "de"
        if req.options is not None:
            self._sync_field_options(field, req.options, src_lang)

        self.db.flush()
        self.db.refresh(field)
        FormPatternLearningService(self.db).record_field_curation(
            field,
            source_language=src_lang,
            organization_id=org.id,
            scope="organization",
        )
        self.db.commit()

        translations = [
            TranslationSchema(
                language=t.language,
                label=t.label,
                help_text=t.help_text,
                placeholder=t.placeholder,
            )
            for t in field.translations
        ]
        options = [
            OptionSchema(
                id=opt.id,
                value=opt.value,
                position=opt.position,
                translations=[
                    OptionTranslationSchema(language=ot.language, label=ot.label)
                    for ot in opt.translations
                ],
            )
            for opt in sorted(field.options, key=lambda o: o.position)
        ]

        return FieldResponse(
            id=field.id,
            key=field.key,
            field_type=field.field_type,
            required=field.required,
            requiredness=field.requiredness,
            position=field.position,
            configuration=field.configuration or {},
            question_key=field.question_key,
            translations=translations,
            options=options,
        )

    def add_field(
        self, user: User, template_id: str, req: FieldCreate
    ) -> FieldResponse:
        org, _ = self._require_org_editor(user)

        template = (
            self.db.query(FormTemplate).filter(FormTemplate.id == template_id).first()
        )
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Template not found."
            )

        latest_version = (
            self.db.query(FormVersion)
            .filter(FormVersion.form_template_id == template.id)
            .order_by(FormVersion.version_number.desc())
            .first()
        )
        if not latest_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Version not found."
            )

        if req.position is None:
            max_pos = (
                self.db.query(func.max(FormField.position))
                .filter(FormField.form_version_id == latest_version.id)
                .scalar()
            )
            field_pos = (max_pos + 1) if max_pos is not None else 0
        else:
            field_pos = req.position

        # Ensure key is unique within this form version (auto-deduplicate e.g. t -> t_2)
        base_key = slugify(req.key) or "field"
        final_key = base_key
        existing_keys = {
            row[0]
            for row in self.db.query(FormField.key)
            .filter(FormField.form_version_id == latest_version.id)
            .all()
        }
        counter = 2
        while final_key in existing_keys:
            final_key = f"{base_key}_{counter}"
            counter += 1

        field = FormField(
            form_version_id=latest_version.id,
            key=final_key,
            field_type=req.field_type,
            required=req.requiredness == "required"
            if req.requiredness
            else req.required,
            requiredness=req.requiredness
            or ("required" if req.required else "optional"),
            position=field_pos,
            question_key=req.question_key.strip() if req.question_key else None,
            configuration=req.configuration or {},
        )
        self.db.add(field)
        self.db.flush()

        if req.translations:
            for t_in in req.translations:
                trans = FormFieldTranslation(
                    form_field_id=field.id,
                    language=t_in.language,
                    label=t_in.label,
                    help_text=t_in.help_text,
                    placeholder=t_in.placeholder,
                )
                self.db.add(trans)
        elif req.label:
            trans = FormFieldTranslation(
                form_field_id=field.id,
                language=latest_version.source_language or "de",
                label=req.label,
                help_text="",
                placeholder="",
            )
            self.db.add(trans)

        src_lang = latest_version.source_language or "de"
        if req.options:
            self._sync_field_options(field, req.options, src_lang)

        self.db.flush()
        self.db.refresh(field)
        FormPatternLearningService(self.db).record_field_curation(
            field,
            source_language=src_lang,
            organization_id=org.id,
            scope="organization",
        )
        self.db.commit()
        self.db.refresh(field)

        translations = [
            TranslationSchema(
                language=t.language,
                label=t.label,
                help_text=t.help_text,
                placeholder=t.placeholder,
            )
            for t in field.translations
        ]

        return FieldResponse(
            id=field.id,
            key=field.key,
            field_type=field.field_type,
            required=field.required,
            requiredness=field.requiredness,
            position=field.position,
            configuration=field.configuration or {},
            question_key=field.question_key,
            translations=translations,
            options=[],
        )

    def delete_field(self, user: User, template_id: str, field_id: str) -> None:
        self._require_org_editor(user)

        field = self.db.query(FormField).filter(FormField.id == field_id).first()
        if not field:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Field not found."
            )

        self.db.delete(field)
        self.db.commit()

    def clear_form_fields(
        self, user: User, template_id: str
    ) -> FormReviewDetailResponse:
        """Deletes all fields from the latest version of the form template."""
        org, _ = self._require_org_editor(user)
        template, latest_version = self._get_form_template_and_version(
            org.id, template_id
        )

        fields = (
            self.db.query(FormField)
            .filter(FormField.form_version_id == latest_version.id)
            .all()
        )
        for f in fields:
            self.db.delete(f)
        self.db.commit()

        return self.get_form_review(user, template_id)

    def delete_form_template(self, user: User, template_id: str) -> None:
        """Deletes a form template and cascades its versions, fields, translations, and options."""
        org, _ = self._require_org_editor(user)
        template = (
            self.db.query(FormTemplate)
            .filter(
                FormTemplate.id == template_id, FormTemplate.organization_id == org.id
            )
            .first()
        )
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Form template not found."
            )

        versions = (
            self.db.query(FormVersion)
            .filter(FormVersion.form_template_id == template.id)
            .all()
        )
        version_ids = [v.id for v in versions]
        if version_ids:
            has_cases = (
                self.db.query(OrganizationCase)
                .filter(OrganizationCase.form_version_id.in_(version_ids))
                .first()
            )
            if has_cases:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot delete form template with submitted citizen cases. Archive it instead.",
                )

            has_sessions = (
                self.db.query(FormSession)
                .filter(FormSession.form_version_id.in_(version_ids))
                .first()
            )
            if has_sessions:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot delete form template with active citizen sessions. Archive it instead.",
                )

            has_exports = (
                self.db.query(FormExport)
                .filter(FormExport.form_version_id.in_(version_ids))
                .first()
            )
            if has_exports:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot delete form template with generated form exports. Archive it instead.",
                )

            # Delete versions
            for v in versions:
                self.db.delete(v)

        self.db.delete(template)
        self.db.commit()

    def reorder_fields(
        self, user: User, template_id: str, field_ids: list[str]
    ) -> list[str]:
        self._require_org_editor(user)

        for pos, fid in enumerate(field_ids, start=1):
            field = self.db.query(FormField).filter(FormField.id == fid).first()
            if field:
                field.position = pos
        self.db.commit()
        return field_ids

    def publish_form(self, user: User, template_id: str) -> FormReviewDetailResponse:
        org, _ = self._require_org_editor(user)
        template, latest_version = self._get_form_template_and_version(
            org.id, template_id
        )

        field_count = (
            self.db.query(func.count(FormField.id))
            .filter(FormField.form_version_id == latest_version.id)
            .scalar()
        )
        if not field_count or field_count == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot publish a form with zero questions. Add at least one field.",
            )

        # Enforce published template slot limits per organization subscription plan
        if latest_version.status != "published":
            published_templates_count = (
                self.db.query(func.count(FormTemplate.id.distinct()))
                .join(FormVersion, FormTemplate.id == FormVersion.form_template_id)
                .filter(
                    FormTemplate.organization_id == org.id,
                    FormVersion.status == "published",
                )
                .scalar()
                or 0
            )
            from app.billing.models import OrganizationSubscription
            from app.billing.services import get_published_template_limit

            subscription = (
                self.db.query(OrganizationSubscription)
                .filter(OrganizationSubscription.organization_id == org.id)
                .first()
            )
            effective_plan = (
                subscription.plan_key if subscription is not None else org.billing_plan
            )
            max_templates = get_published_template_limit(effective_plan)
            if published_templates_count >= max_templates:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail=(
                        f"Publishing slot limit reached for your '{effective_plan}' plan "
                        f"({published_templates_count}/{max_templates} active templates). "
                        "Please upgrade your workspace plan to publish more form templates."
                    ),
                )

        latest_version.status = "published"
        latest_version.published_at = func.now()
        FormPatternLearningService(self.db).record_published_version(
            latest_version,
            source_language=latest_version.source_language or "de",
            organization_id=org.id,
            promote_global=(org.verification_status == "verified_official"),
        )
        self.db.commit()

        return self.get_form_review(user, template_id)

    def archive_form(self, user: User, template_id: str) -> FormReviewDetailResponse:
        org, _ = self._require_org_editor(user)
        template, latest_version = self._get_form_template_and_version(
            org.id, template_id
        )

        latest_version.status = "archived"
        self.db.commit()

        return self.get_form_review(user, template_id)

    def get_source_pdf_bytes(self, user: User, template_id: str) -> tuple[bytes, str]:
        org, _ = self._require_org_viewer(user)
        template, latest_version = self._get_form_template_and_version(
            org.id, template_id
        )
        if not latest_version.source_pdf_storage_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source PDF document not found for this form.",
            )

        pdf_bytes = self.storage.get_bytes(latest_version.source_pdf_storage_path)
        return pdf_bytes, f"{template.key}.pdf"

    def get_form_page_preview_png(
        self, user: User, template_id: str, page_number: int = 1
    ) -> bytes:
        org, _ = self._require_org_viewer(user)
        template, latest_version = self._get_form_template_and_version(
            org.id, template_id
        )
        if not latest_version.source_pdf_storage_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source PDF document not found for this form.",
            )

        pdf_bytes = self.storage.get_bytes(latest_version.source_pdf_storage_path)
        try:
            return render_pdf_page_png(pdf_bytes, page_number)
        except ValueError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            ) from e

    async def translate_field_label(
        self,
        user: User,
        text: str,
        source_language: str,
        target_languages: list[str],
    ) -> dict[str, str]:
        """Translates a field label from source language into target guidance languages."""
        self._require_org_viewer(user)
        clean_text = text.strip()
        if not clean_text:
            return {}

        # Known fallback dictionary for mock/offline testing
        mock_dictionary: dict[str, dict[str, str]] = {
            "ar": {
                "einzugsbestätigung": "تأكيد السكن والانتقال من المؤجر",
                "auszugsbestätigung": "تأكيد مغادرة السكن من المؤجر",
                "vorname": "الاسم الأول",
                "nachname": "اسم العائلة",
                "geburtsdatum": "تاريخ الميلاد",
                "aktuelle anschrift": "العنوان الحالي",
                "datum einzug": "تاريخ الانتقال للسكن",
                "erste person": "الشخص الأول",
                "zweite person": "الشخص الثاني",
                "dritte person": "الشخص الثالث",
                "vierte person": "الشخص الرابع",
                "eigentümer": "مالك السكن",
                "unterschrift": "التوقيع",
            },
            "en": {
                "einzugsbestätigung": "Landlord Move-In Confirmation (Section 19 BMG)",
                "auszugsbestätigung": "Landlord Move-Out Confirmation",
                "vorname": "First Name",
                "nachname": "Last Name",
                "geburtsdatum": "Date of Birth",
                "aktuelle anschrift": "Current Address",
                "datum einzug": "Move-In Date",
                "erste person": "First Person",
                "zweite person": "Second Person",
                "dritte person": "Third Person",
                "vierte person": "Fourth Person",
                "eigentümer": "Property Owner",
                "unterschrift": "Signature",
            },
            "fr": {
                "einzugsbestätigung": "Attestation d'emménagement du bailleur",
                "auszugsbestätigung": "Attestation de déménagement du bailleur",
                "vorname": "Prénom",
                "nachname": "Nom de famille",
                "geburtsdatum": "Date de naissance",
                "aktuelle anschrift": "Adresse actuelle",
                "datum einzug": "Date d'emménagement",
                "unterschrift": "Signature",
            },
            "tr": {
                "einzugsbestätigung": "Ev Sahibi Taşınma Onayı",
                "auszugsbestätigung": "Ev Sahibi Ayrılma Onayı",
                "vorname": "Ad",
                "nachname": "Soyad",
                "geburtsdatum": "Doğum Tarihi",
                "aktuelle anschrift": "Mevcut Adres",
                "datum einzug": "Taşınma Tarihi",
                "unterschrift": "İmza",
            },
            "uk": {
                "einzugsbestätigung": "Підтвердження орендодавця про вселення",
                "auszugsbestätigung": "Підтвердження орендодавця про виселення",
                "vorname": "Ім'я",
                "nachname": "Прізвище",
                "geburtsdatum": "Дата народження",
                "aktuelle anschrift": "Поточна адреса",
                "datum einzug": "Дата вселення",
                "unterschrift": "Підпис",
            },
        }

        from app.ai.factory import build_provider
        from app.ai.text_translation import translate_text
        from app.translation.memory import TranslationMemoryService

        tm_service = TranslationMemoryService(self.db)
        results: dict[str, str] = {}

        # 1. Lookup in Translation Memory (0ms, €0 COGS cache)
        cached_translations = tm_service.get_translations(
            clean_text, source_language, target_languages
        )
        for t_lang, t_val in cached_translations.items():
            results[t_lang] = t_val

        # 2. Determine which languages still need translation
        remaining_languages = [
            lang
            for lang in target_languages
            if lang.strip().lower() not in results
            and lang.strip().lower() != source_language.lower()
        ]

        if not remaining_languages:
            for target_lang in target_languages:
                if target_lang.strip().lower() == source_language.lower():
                    results[target_lang.strip().lower()] = clean_text
            return results

        ai_provider = build_provider()
        new_translations_to_cache: dict[str, str] = {}

        for target_lang in remaining_languages:
            target_lang = target_lang.strip().lower()
            try:
                res = await translate_text(
                    ai_provider, clean_text, source_language, target_lang
                )
                if res.translated_text and res.translated_text != clean_text:
                    translated_val = res.translated_text
                else:
                    matched = None
                    text_lower = clean_text.lower()
                    for keyword, trans in mock_dictionary.get(target_lang, {}).items():
                        if keyword in text_lower:
                            matched = trans
                            break
                    translated_val = matched or f"[{target_lang.upper()}] {clean_text}"
                results[target_lang] = translated_val
                new_translations_to_cache[target_lang] = translated_val
            except Exception as e:
                logger.warning("Field translation to %s failed: %s", target_lang, e)
                results[target_lang] = clean_text

        # 3. Store newly translated terms into Translation Memory
        if new_translations_to_cache:
            tm_service.bulk_save_translations(
                text=clean_text,
                source_language=source_language,
                translations=new_translations_to_cache,
                provider="gemini",
            )

        for target_lang in target_languages:
            if target_lang.strip().lower() == source_language.lower():
                results[target_lang.strip().lower()] = clean_text

        return results

    def _sync_field_options(
        self,
        field: FormField,
        options_in: list[OptionSchema],
        source_language: str,
    ) -> None:
        """Replace a field's FormFieldOption and FormFieldOptionTranslation rows."""
        for existing_opt in list(field.options or []):
            self.db.delete(existing_opt)
        self.db.flush()

        for idx, opt_in in enumerate(
            sorted(options_in, key=lambda o: (o.position, o.value))
        ):
            val = opt_in.value.strip()
            if not val:
                continue
            opt_row = FormFieldOption(
                form_field_id=field.id,
                value=val,
                position=idx + 1,
            )
            self.db.add(opt_row)
            self.db.flush()

            has_source = False
            for ot in opt_in.translations or []:
                lbl = ot.label.strip()
                if not lbl:
                    continue
                if ot.language == source_language:
                    has_source = True
                self.db.add(
                    FormFieldOptionTranslation(
                        form_field_option_id=opt_row.id,
                        language=ot.language,
                        label=lbl,
                    )
                )
            if not has_source:
                self.db.add(
                    FormFieldOptionTranslation(
                        form_field_option_id=opt_row.id,
                        language=source_language,
                        label=val,
                    )
                )

    def combine_fields_into_choice(
        self,
        user: User,
        template_id: str,
        req: CombineChoiceFieldsRequest,
    ) -> FormReviewDetailResponse:
        """Merge 2+ selected fields/checkboxes into a single choice question."""
        org, _ = self._require_org_editor(user)
        _template, latest_version = self._get_form_template_and_version(
            org.id, template_id
        )

        if len(req.field_ids) < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Select at least 2 fields to combine into a choice question.",
            )
        if req.field_type not in ("single_choice", "multiple_choice", "choice"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Choice field_type must be single_choice or multiple_choice.",
            )

        selected = (
            self.db.query(FormField)
            .filter(
                FormField.form_version_id == latest_version.id,
                FormField.id.in_(req.field_ids),
            )
            .options(joinedload(FormField.translations), joinedload(FormField.options))
            .all()
        )
        by_id = {f.id: f for f in selected}
        ordered_selected = [by_id[fid] for fid in req.field_ids if fid in by_id]
        if len(ordered_selected) < 2:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more selected fields were not found in this form version.",
            )

        src_lang = latest_version.source_language or "de"
        primary = ordered_selected[0]
        option_boxes: list[dict[str, Any]] = []
        options_schema: list[OptionSchema] = []
        all_bboxes: list[list[float]] = []
        seen_vals: set[str] = set()
        learned_options_payload: list[dict[str, Any]] = []

        for idx, f in enumerate(ordered_selected):
            src_tr = next(
                (t for t in f.translations if t.language == src_lang),
                f.translations[0] if f.translations else None,
            )
            custom_lbl = (
                req.option_labels[idx].strip()
                if req.option_labels and idx < len(req.option_labels)
                else ""
            )
            opt_label = custom_lbl or (
                src_tr.label if src_tr else f.key.replace("_", " ")
            )
            val_base = slugify(opt_label) or f"option_{idx + 1}"
            opt_val = val_base
            suffix = 2
            while opt_val in seen_vals:
                opt_val = f"{val_base}_{suffix}"
                suffix += 1
            seen_vals.add(opt_val)

            options_schema.append(
                OptionSchema(
                    value=opt_val,
                    position=idx + 1,
                    translations=[
                        OptionTranslationSchema(language=src_lang, label=opt_label)
                    ],
                )
            )
            learned_options_payload.append(
                {"value": opt_val, "translations": {src_lang: opt_label}}
            )

            cfg = f.configuration if isinstance(f.configuration, dict) else {}
            bbox = cfg.get("bbox")
            if isinstance(bbox, list) and len(bbox) == 4:
                float_box = [float(b) for b in bbox]
                all_bboxes.append(float_box)
                option_boxes.append(
                    {
                        "value": opt_val,
                        "label": opt_label,
                        "page": int(cfg.get("page", 1)),
                        "bbox": float_box,
                    }
                )

        new_cfg = dict(primary.configuration or {})
        if all_bboxes:
            new_cfg["bbox"] = [
                round(min(b[0] for b in all_bboxes), 1),
                round(min(b[1] for b in all_bboxes), 1),
                round(max(b[2] for b in all_bboxes), 1),
                round(max(b[3] for b in all_bboxes), 1),
            ]
        if option_boxes:
            new_cfg["option_boxes"] = option_boxes

        primary.field_type = req.field_type
        primary.requiredness = req.requiredness or primary.requiredness
        primary.required = primary.requiredness == "required"
        if req.question_key is not None:
            primary.question_key = req.question_key.strip() or None
        primary.configuration = new_cfg

        clean_label = req.label.strip() or "Choice"
        existing_src_tr = next(
            (t for t in primary.translations if t.language == src_lang), None
        )
        if existing_src_tr:
            existing_src_tr.label = clean_label
        else:
            self.db.add(
                FormFieldTranslation(
                    form_field_id=primary.id,
                    language=src_lang,
                    label=clean_label,
                )
            )

        self._sync_field_options(primary, options_schema, src_lang)

        for absorbed in ordered_selected[1:]:
            self.db.delete(absorbed)
        self.db.flush()

        # Re-normalize remaining positions cleanly
        remaining = (
            self.db.query(FormField)
            .filter(FormField.form_version_id == latest_version.id)
            .order_by(FormField.position.asc())
            .all()
        )
        for pos, rf in enumerate(remaining):
            rf.position = pos

        FormPatternLearningService(self.db).record_choice_group_curation(
            label=clean_label,
            options=learned_options_payload,
            source_language=src_lang,
            field_type=primary.field_type,
            translations={src_lang: {"label": clean_label}},
            organization_id=org.id,
            scope="organization",
            question_key=primary.question_key,
            requiredness=primary.requiredness,
        )
        self.db.commit()
        return self.get_form_review(user, template_id)

    def group_fields_into_table_row(
        self,
        user: User,
        template_id: str,
        req: GroupTableRowRequest,
    ) -> FormReviewDetailResponse:
        """Group selected fields into one table row and isolate Row 2+ from applicant Vault keys."""
        org, _ = self._require_org_editor(user)
        _template, latest_version = self._get_form_template_and_version(
            org.id, template_id
        )

        if not req.field_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Select at least 1 field to assign to a table row.",
            )

        selected = (
            self.db.query(FormField)
            .filter(
                FormField.form_version_id == latest_version.id,
                FormField.id.in_(req.field_ids),
            )
            .options(joinedload(FormField.translations))
            .all()
        )
        if len(selected) != len(set(req.field_ids)):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="One or more selected fields were not found in this form version.",
            )

        src_lang = latest_version.source_language or "de"
        t_key = slugify(req.table_key or req.table_title or "table") or "table"

        def _x_sort_key(f: FormField) -> tuple[float, int]:
            cfg = f.configuration if isinstance(f.configuration, dict) else {}
            bbox = cfg.get("bbox")
            x0 = (
                float(bbox[0])
                if isinstance(bbox, list) and len(bbox) == 4
                else float(f.position)
            )
            return (x0, f.position)

        ordered = sorted(selected, key=_x_sort_key)

        all_fields = (
            self.db.query(FormField)
            .filter(FormField.form_version_id == latest_version.id)
            .all()
        )
        existing_rows: set[int] = {req.row_index}
        for af in all_fields:
            tbl = (
                (af.configuration or {}).get("table")
                if isinstance(af.configuration, dict)
                else None
            )
            if (
                isinstance(tbl, dict)
                and tbl.get("table_key") == t_key
                and tbl.get("row_index") is not None
            ):
                existing_rows.add(int(tbl["row_index"]))
        total_rows = max(existing_rows)

        row_role = req.row_role or ("applicant" if req.row_index == 1 else "member")
        row_label = req.row_label or (
            "Applicant" if req.row_index == 1 else f"Row {req.row_index}"
        )

        for col_idx, f in enumerate(ordered):
            src_tr = next(
                (t for t in f.translations if t.language == src_lang),
                f.translations[0] if f.translations else None,
            )
            col_hdr = src_tr.label if src_tr else f.key.replace("_", " ")
            cfg = dict(f.configuration or {})
            cfg["table"] = {
                "table_key": t_key,
                "table_title": req.table_title.strip()
                or t_key.replace("_", " ").title(),
                "table_description": req.table_description,
                "row_index": req.row_index,
                "total_rows": total_rows,
                "row_label": row_label,
                "row_role": row_role,
                "col_index": col_idx,
                "column_header": col_hdr,
            }
            f.configuration = cfg
            if req.row_index >= 2:
                f.question_key = None
                f.requiredness = "optional"
                f.required = False

        # Keep total_rows synchronized on sibling rows of the same table
        rows_by_idx: dict[int, list[FormField]] = {}
        for af in all_fields:
            cfg = af.configuration if isinstance(af.configuration, dict) else None
            tbl = cfg.get("table") if isinstance(cfg, dict) else None
            if (
                isinstance(tbl, dict)
                and tbl.get("table_key") == t_key
                and tbl.get("row_index") is not None
            ):
                new_tbl = dict(tbl)
                new_tbl["total_rows"] = total_rows
                new_cfg = dict(cfg or {})
                new_cfg["table"] = new_tbl
                af.configuration = new_cfg
                rows_by_idx.setdefault(int(tbl["row_index"]), []).append(af)

        FormPatternLearningService(self.db).record_table_schema_curation(
            table_key=t_key,
            table_title=req.table_title,
            row_fields_by_index=rows_by_idx,
            source_language=src_lang,
            organization_id=org.id,
            scope="organization",
        )
        self.db.commit()
        return self.get_form_review(user, template_id)

    def sync_table_columns(
        self,
        user: User,
        template_id: str,
        table_key: str,
        req: SyncTableColumnsRequest,
    ) -> FormReviewDetailResponse:
        """Apply source row's column types, options, and labels to all rows in the table."""
        org, _ = self._require_org_editor(user)
        _template, latest_version = self._get_form_template_and_version(
            org.id, template_id
        )

        all_fields = (
            self.db.query(FormField)
            .filter(FormField.form_version_id == latest_version.id)
            .options(
                joinedload(FormField.translations),
                joinedload(FormField.options).joinedload(FormFieldOption.translations),
            )
            .order_by(FormField.position.asc())
            .all()
        )
        rows_by_idx: dict[int, list[FormField]] = {}
        table_title = table_key
        for f in all_fields:
            tbl = (
                (f.configuration or {}).get("table")
                if isinstance(f.configuration, dict)
                else None
            )
            if (
                isinstance(tbl, dict)
                and tbl.get("table_key") == table_key
                and tbl.get("row_index") is not None
            ):
                r_idx = int(tbl["row_index"])
                rows_by_idx.setdefault(r_idx, []).append(f)
                if tbl.get("table_title"):
                    table_title = str(tbl["table_title"])

        source_row = rows_by_idx.get(req.source_row_index)
        if not source_row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source table row not found.",
            )

        src_lang = latest_version.source_language or "de"
        source_by_col: dict[int, FormField] = {}
        for idx, sf in enumerate(
            sorted(
                source_row,
                key=lambda item: int(
                    ((item.configuration or {}).get("table") or {}).get(
                        "col_index", item.position
                    )
                ),
            )
        ):
            c_idx = int(
                ((sf.configuration or {}).get("table") or {}).get("col_index", idx)
            )
            source_by_col[c_idx] = sf

        for r_idx, row_fields in rows_by_idx.items():
            if r_idx == req.source_row_index:
                continue
            for idx, tf in enumerate(
                sorted(
                    row_fields,
                    key=lambda item: int(
                        ((item.configuration or {}).get("table") or {}).get(
                            "col_index", item.position
                        )
                    ),
                )
            ):
                t_tbl = dict((tf.configuration or {}).get("table") or {})
                c_idx = int(t_tbl.get("col_index", idx))
                src_field = source_by_col.get(c_idx)
                if not src_field:
                    continue

                tf.field_type = src_field.field_type
                if r_idx >= 2:
                    tf.question_key = None
                    tf.requiredness = "optional"
                    tf.required = False

                s_tbl = (src_field.configuration or {}).get("table") or {}
                if s_tbl.get("column_header"):
                    t_tbl["column_header"] = s_tbl["column_header"]
                    new_cfg = dict(tf.configuration or {})
                    new_cfg["table"] = t_tbl
                    tf.configuration = new_cfg

                for st in src_field.translations or []:
                    existing_tt = next(
                        (tt for tt in tf.translations if tt.language == st.language),
                        None,
                    )
                    if existing_tt:
                        existing_tt.label = st.label
                        existing_tt.help_text = st.help_text
                        existing_tt.placeholder = st.placeholder
                    else:
                        self.db.add(
                            FormFieldTranslation(
                                form_field_id=tf.id,
                                language=st.language,
                                label=st.label,
                                help_text=st.help_text,
                                placeholder=st.placeholder,
                            )
                        )

                if src_field.options:
                    copied_opts = [
                        OptionSchema(
                            value=opt.value,
                            position=opt.position,
                            translations=[
                                OptionTranslationSchema(
                                    language=ot.language, label=ot.label
                                )
                                for ot in (opt.translations or [])
                            ],
                        )
                        for opt in sorted(src_field.options, key=lambda o: o.position)
                    ]
                    self._sync_field_options(tf, copied_opts, src_lang)

        self.db.flush()
        FormPatternLearningService(self.db).record_table_schema_curation(
            table_key=table_key,
            table_title=table_title,
            row_fields_by_index=rows_by_idx,
            source_language=src_lang,
            organization_id=org.id,
            scope="organization",
        )
        self.db.commit()
        return self.get_form_review(user, template_id)
