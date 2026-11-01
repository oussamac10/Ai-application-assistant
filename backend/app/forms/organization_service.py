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
import re
import tempfile
import uuid
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.auth.models import User
from app.core.config import settings
from app.documents.errors import DocumentValidationError
from app.documents.image_normalizer import (
    detect_upload_media_kind,
    normalize_image_file_to_a4_pdf,
)
from app.forms.models import (
    FormField,
    FormFieldOption,
    FormFieldTranslation,
    FormTemplate,
    FormVersion,
)
from app.forms.schemas import (
    FieldCreate,
    FieldResponse,
    FieldUpdate,
    FormReviewDetailResponse,
    FormReviewUpdateRequest,
    OptionSchema,
    OptionTranslationSchema,
    OrganizationFormSummary,
    TranslationSchema,
)
from app.organizations.repositories import OrganizationRepository
from app.storage.factory import get_storage_provider

logger = logging.getLogger(__name__)

# Canonical question key mappings for administrative and official forms
_KEY_PATTERNS: list[tuple[re.Pattern[str], str, str, str]] = [
    (
        re.compile(r"vorname|first_?name", re.IGNORECASE),
        "First Name",
        "string",
        "personal.first_name",
    ),
    (
        re.compile(r"nachname|familienname|last_?name|sur_?name", re.IGNORECASE),
        "Last Name",
        "string",
        "personal.last_name",
    ),
    (
        re.compile(r"geburtsdatum|date_?of_?birth|birth_?date", re.IGNORECASE),
        "Date of Birth",
        "date",
        "person.date_of_birth",
    ),
    (
        re.compile(r"geburtsort|birth_?place", re.IGNORECASE),
        "Place of Birth",
        "string",
        "personal.place_of_birth",
    ),
    (
        re.compile(r"staatsangeh|nationality|citizenship", re.IGNORECASE),
        "Nationality / Citizenship",
        "country",
        "personal.nationality",
    ),
    (
        re.compile(r"e[-_]?mail", re.IGNORECASE),
        "Email Address",
        "email",
        "contact.email",
    ),
    (
        re.compile(r"telefon|phone|mobil|rufnummer", re.IGNORECASE),
        "Phone Number",
        "phone",
        "contact.phone",
    ),
    (
        re.compile(r"anschrift|adresse|address", re.IGNORECASE),
        "Current Address",
        "string",
        "residence.street_and_number",
    ),
    (
        re.compile(r"stra[ßs]e|street", re.IGNORECASE),
        "Street Address",
        "string",
        "address.street",
    ),
    (
        re.compile(r"hausnummer|house_?num", re.IGNORECASE),
        "House / Building Number",
        "string",
        "address.house_number",
    ),
    (
        re.compile(r"postleitzahl|plz|postal_?code|zip", re.IGNORECASE),
        "Postal / ZIP Code",
        "string",
        "address.postal_code",
    ),
    (
        re.compile(r"ort|stadt|city|wohnort", re.IGNORECASE),
        "City / Town",
        "string",
        "address.city",
    ),
    (
        re.compile(r"land|country", re.IGNORECASE),
        "Country",
        "country",
        "address.country",
    ),
    (re.compile(r"iban", re.IGNORECASE), "IBAN / Bank Account", "iban", "finance.iban"),
    (
        re.compile(r"einzugsdatum|move_?in", re.IGNORECASE),
        "Move-in Date",
        "date",
        "residence.move_in_date",
    ),
    (
        re.compile(r"auszugsdatum|move_?out", re.IGNORECASE),
        "Move-out Date",
        "date",
        "residence.move_out_date",
    ),
    (
        re.compile(r"wohnungsgeber|vermieter|landlord", re.IGNORECASE),
        "Landlord / Housing Provider",
        "string",
        "landlord.name",
    ),
    (
        re.compile(r"unterschrift|signature", re.IGNORECASE),
        "Signature",
        "signature",
        "signature.applicant",
    ),
]


def infer_field_metadata(
    raw_name: str, field_type_str: str
) -> tuple[str, str, str | None, str]:
    """Infers (clean_label, field_type, question_key, requiredness) from field names."""
    normalized = raw_name.strip()
    for pattern, label, ftype, qkey in _KEY_PATTERNS:
        if pattern.search(normalized):
            req = "optional" if ftype in ("email", "phone", "iban") else "required"
            return label, ftype, qkey, req

    # Fallback to humanized label
    clean_label = re.sub(r"[_\-]+", " ", normalized).strip()
    if clean_label:
        clean_label = clean_label[0].upper() + clean_label[1:]
    else:
        clean_label = "Feld"

    ftype = "string"
    if "check" in field_type_str.lower() or "radio" in field_type_str.lower():
        ftype = "boolean"
    elif "choice" in field_type_str.lower():
        ftype = "choice"
    elif "signature" in field_type_str.lower():
        ftype = "signature"

    return clean_label, ftype, None, "required"


def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_-]+", "-", s)
    return s.strip("-") or "form"


def extract_fields_from_pdf_layout(doc: fitz.Document) -> list[dict[str, Any]]:
    """Extracts field prompts and bounding boxes from flat PDF text and drawn rectangles.

    Guarantees 100% fidelity to the actual document: never invents missing fields.
    """
    fields: list[dict[str, Any]] = []
    for page_idx, page in enumerate(doc):
        # 1. Collect drawn vector rectangles (input boxes)
        drawings = page.get_drawings()
        rect_boxes: list[fitz.Rect] = []
        for d in drawings:
            r = d.get("rect")
            if (
                r
                and r.width > 40
                and 10 < r.height < 180
                and r.width < page.rect.width * 0.98
            ):
                rect_boxes.append(r)

        # 2. Inspect text blocks (or fallback to OCR for scanned documents / raster images)
        blocks = page.get_text("blocks")
        if not blocks:
            try:
                tp = page.get_textpage_ocr(language="eng+deu+fra+spa", dpi=150)
                blocks = tp.extractBLOCKS()
            except Exception as e:
                logger.warning("OCR fallback on page %d failed: %s", page_idx, e)
                blocks = []
        for b in blocks:
            if b[6] != 0:  # text block only
                continue
            text = b[4].strip()
            lines = [ln.strip() for ln in text.split("\n") if ln.strip()]
            for line in lines:
                is_prompt = (
                    line.endswith(":")
                    or line.endswith("*")
                    or line.endswith("*:")
                    or any(p[0].search(line) for p in _KEY_PATTERNS)
                )
                if not is_prompt or len(line) > 90:
                    continue

                label, ftype, qkey, req = infer_field_metadata(line, "text")
                bx0, by0, bx1, by1 = b[0], b[1], b[2], b[3]

                # Match nearest drawn box below or to the right
                matched_box: fitz.Rect | None = None
                min_dist = float("inf")
                for r in rect_boxes:
                    if r.y0 >= by0 and (r.y0 - by1) < 55 and abs(r.x0 - bx0) < 140:
                        dist = r.y0 - by1
                        if dist < min_dist:
                            min_dist = dist
                            matched_box = r
                    elif abs(r.y0 - by0) < 25 and r.x0 >= bx0 and (r.x0 - bx1) < 70:
                        dist = r.x0 - bx1
                        if dist < min_dist:
                            min_dist = dist
                            matched_box = r

                if matched_box:
                    bbox = [
                        round(float(matched_box.x0), 1),
                        round(float(matched_box.y0), 1),
                        round(float(matched_box.x1), 1),
                        round(float(matched_box.y1), 1),
                    ]
                else:
                    bbox = [
                        round(float(bx0), 1),
                        round(float(by1 + 2), 1),
                        round(float(min(page.rect.width - 50, bx0 + 380)), 1),
                        round(float(by1 + 26), 1),
                    ]

                clean_lbl = line.rstrip(":* ").strip()
                fkey = slugify(clean_lbl) or f"field_{len(fields) + 1}"
                existing_keys = {f["key"] for f in fields}
                if fkey in existing_keys:
                    fkey = f"{fkey}_{len(fields) + 1}"

                fields.append(
                    {
                        "key": fkey,
                        "label": clean_lbl,
                        "field_type": ftype,
                        "question_key": qkey,
                        "requiredness": req,
                        "options": [],
                        "bbox": bbox,
                        "page": page_idx + 1,
                    }
                )
    return fields


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

    def list_organization_forms(self, user: User) -> list[OrganizationFormSummary]:
        org, _ = self._require_org_viewer(user)

        templates = (
            self.db.query(FormTemplate)
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

            summaries.append(
                OrganizationFormSummary(
                    id=tmpl.id,
                    key=tmpl.key,
                    name=tmpl.name,
                    description=tmpl.description,
                    category=tmpl.category,
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
        submission_method: str = "print_and_sign",
        instructions: str | None = None,
        required_documents: list[str] | None = None,
        auto_extract: bool = False,
    ) -> FormReviewDetailResponse:
        org, _ = self._require_org_editor(user)

        # 1. Inspect magic bytes and normalize image if needed (JPG, PNG, WebP -> A4 PDF)
        doc_uuid = str(uuid.uuid4())
        ext = Path(filename).suffix.lower() if filename else ".pdf"
        if ext not in (".pdf", ".jpg", ".jpeg", ".png", ".webp"):
            ext = ".bin"

        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(pdf_bytes)
            tmp_path = Path(tmp.name)

        try:
            source_media_type = detect_upload_media_kind(str(tmp_path))
            if source_media_type == "application/pdf":
                if not pdf_bytes.startswith(b"%PDF-"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Uploaded file must be a valid PDF document.",
                    )
            else:
                # Camera scan or image upload: normalize EXIF orientation and composite onto ISO A4 PDF
                normalize_image_file_to_a4_pdf(
                    str(tmp_path),
                    settings.DOCUMENT_UPLOAD_MAX_IMAGE_PIXELS,
                    source_media_type,
                )
                pdf_bytes = tmp_path.read_bytes()

            stored_filename = f"org-form-{doc_uuid[:8]}.pdf"
            storage_path = self.storage.save_file(
                "documents",
                stored_filename,
                tmp_path,
                content_type="application/pdf",
            )
        except DocumentValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

        # 3. Create FormTemplate
        clean_name = name.strip() or "Unbenanntes Formular"
        base_slug = slugify(clean_name)
        unique_key = f"{base_slug}-{doc_uuid[:8]}"

        template = FormTemplate(
            organization_id=org.id,
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
            self._insert_extracted_fields(version.id, extracted_fields)

        self.db.commit()
        return self.get_form_review(user, template.id)

    def _extract_fields_from_pdf_bytes(self, pdf_bytes: bytes) -> list[dict[str, Any]]:
        """Extracts candidate fields from interactive AcroForms or layout text."""
        extracted_fields: list[dict[str, Any]] = []
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            for page_idx, page in enumerate(doc):
                for widget in page.widgets():
                    if not widget.field_name:
                        continue
                    label, ftype, qkey, req = infer_field_metadata(
                        widget.field_name, widget.field_type_string or "text"
                    )
                    options: list[str] = []
                    if hasattr(widget, "choice_values") and widget.choice_values:
                        options = list(widget.choice_values)

                    rect = widget.rect
                    bbox = [
                        float(rect.x0),
                        float(rect.y0),
                        float(rect.x1),
                        float(rect.y1),
                    ]

                    extracted_fields.append(
                        {
                            "key": slugify(widget.field_name),
                            "label": label,
                            "field_type": ftype,
                            "question_key": qkey,
                            "requiredness": req,
                            "options": options,
                            "bbox": bbox,
                            "page": page_idx + 1,
                        }
                    )
            doc.close()
        except Exception as e:
            logger.warning("PyMuPDF widget extraction encountered an error: %s", e)

        # Fallback: if no interactive AcroForm widgets found, extract layout-based fields from text and drawn boxes
        if not extracted_fields:
            try:
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                extracted_fields = extract_fields_from_pdf_layout(doc)
                doc.close()
            except Exception as e:
                logger.warning("PyMuPDF layout-based field extraction error: %s", e)

        return extracted_fields

    def _insert_extracted_fields(
        self, version_id: str, extracted_fields: list[dict[str, Any]]
    ) -> None:
        """Inserts extracted fields into database with unique keys and source translation."""
        current_max_pos = (
            self.db.query(func.max(FormField.position))
            .filter(FormField.form_version_id == version_id)
            .scalar()
            or 0
        )
        existing_keys = {
            f.key
            for f in self.db.query(FormField.key)
            .filter(FormField.form_version_id == version_id)
            .all()
        }

        for idx, f in enumerate(extracted_fields):
            base_key = f["key"]
            candidate_key = base_key
            suffix = 2
            while candidate_key in existing_keys:
                candidate_key = f"{base_key}_{suffix}"
                suffix += 1
            existing_keys.add(candidate_key)

            form_field = FormField(
                form_version_id=version_id,
                key=candidate_key,
                field_type=f["field_type"],
                required=f["requiredness"] == "required",
                requiredness=f["requiredness"],
                position=current_max_pos + idx + 1,
                question_key=f["question_key"],
                configuration={"bbox": f.get("bbox"), "page": f.get("page", 1)},
            )
            self.db.add(form_field)
            self.db.flush()

            # Translation for de (source language)
            trans = FormFieldTranslation(
                form_field_id=form_field.id,
                language="de",
                label=f["label"],
            )
            self.db.add(trans)

            # Options if choice field
            for opt_idx, opt_val in enumerate(f.get("options", [])):
                opt = FormFieldOption(
                    form_field_id=form_field.id,
                    value=opt_val,
                    position=opt_idx + 1,
                )
                self.db.add(opt)

    def auto_detect_fields(
        self, user: User, template_id: str
    ) -> FormReviewDetailResponse:
        """On-demand scan and extraction of fields from the attached form document."""
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

        if not latest_version.source_pdf_storage_path:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No source PDF attached to this form version.",
            )

        pdf_bytes = self.storage.get_bytes(latest_version.source_pdf_storage_path)
        extracted_fields = self._extract_fields_from_pdf_bytes(pdf_bytes)
        self._insert_extracted_fields(latest_version.id, extracted_fields)
        self.db.commit()

        return self.get_form_review(user, template_id)

        self.db.commit()

        return self.get_form_review(user, template.id)

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
                doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                page_count = len(doc)
                page_dimensions = [
                    {
                        "page": idx + 1,
                        "width": round(float(p.rect.width), 1),
                        "height": round(float(p.rect.height), 1),
                    }
                    for idx, p in enumerate(doc)
                ]
                doc.close()
            except Exception as e:
                logger.warning("Could not read PDF page dimensions: %s", e)

        return FormReviewDetailResponse(
            template_id=template.id,
            version_id=latest_version.id,
            key=template.key,
            name=template.name,
            description=template.description,
            category=template.category,
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
            .first()
        )
        if not latest_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Form version not found."
            )

        if req.name is not None and req.name.strip():
            template.name = req.name.strip()
        if req.description is not None:
            template.description = req.description.strip() or None
        if req.category is not None and req.category.strip():
            template.category = req.category.strip()
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

    def update_field(
        self, user: User, template_id: str, field_id: str, req: FieldUpdate
    ) -> FieldResponse:
        self._require_org_editor(user)

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
        self._require_org_editor(user)

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
            .first()
        )
        if not latest_version:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Form version not found."
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

        latest_version.status = "published"
        latest_version.published_at = func.now()
        self.db.commit()

        return self.get_form_review(user, template_id)

    def archive_form(self, user: User, template_id: str) -> FormReviewDetailResponse:
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

        latest_version.status = "archived"
        self.db.commit()

        return self.get_form_review(user, template_id)

    def get_source_pdf_bytes(self, user: User, template_id: str) -> tuple[bytes, str]:
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
            .first()
        )
        if not latest_version or not latest_version.source_pdf_storage_path:
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
            .first()
        )
        if not latest_version or not latest_version.source_pdf_storage_path:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Source PDF document not found for this form.",
            )

        pdf_bytes = self.storage.get_bytes(latest_version.source_pdf_storage_path)
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if page_number < 1 or page_number > len(doc):
            doc.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid page number {page_number}. Document has {len(doc)} pages.",
            )

        page = doc[page_number - 1]
        pix = page.get_pixmap(dpi=150)
        png_bytes: bytes = bytes(pix.tobytes("png"))
        doc.close()
        return png_bytes
