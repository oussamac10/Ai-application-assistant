import json
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_user, verify_csrf
from app.auth.models import User
from app.database.session import get_db
from app.forms.organization_service import OrganizationFormService
from app.forms.schemas import (
    CategoryFormsAssignRequest,
    FieldCreate,
    FieldResponse,
    FieldUpdate,
    FormCategoryUpdateRequest,
    FormReviewDetailResponse,
    FormReviewUpdateRequest,
    OrganizationFormSummary,
    TranslateFieldRequest,
    TranslateFieldResponse,
)
from app.organizations.schemas import (
    CandidateInviteRedemptionResponse,
    CaseCreateRequest,
    CaseRead,
    CaseUpdateRequest,
    OrganizationCategoryCreate,
    OrganizationCategoryRead,
    OrganizationCategoryUpdate,
    OrganizationCreateRequest,
    OrganizationMemberInvite,
    OrganizationMemberRead,
    OrganizationMemberRoleUpdate,
    OrganizationProfileUpdate,
    OrganizationRead,
    OrganizationVerificationRequest,
    PublicOrganizationDetail,
    PublicOrganizationSummary,
)
from app.organizations.services import OrganizationService

router = APIRouter(tags=["organizations-and-cases"])


@router.get("/organizations/current", response_model=OrganizationRead)
def get_current_organization(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> Any:
    service = OrganizationService(db)
    return service.get_user_organization(user)


@router.post(
    "/organizations",
    response_model=OrganizationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_organization(
    body: OrganizationCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    service = OrganizationService(db)
    service.create_organization_for_user(
        user=user,
        name=body.name,
        organization_type=body.organization_type,
        official_website_url=body.official_website_url,
    )
    return service.get_user_organization(user)


@router.patch("/organizations/current", response_model=OrganizationRead)
def update_current_organization(
    body: OrganizationProfileUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    service = OrganizationService(db)
    return service.update_profile(user, body)


@router.post("/organizations/current/verification", response_model=OrganizationRead)
def submit_organization_verification(
    body: OrganizationVerificationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    service = OrganizationService(db)
    return service.submit_verification(user, body)


@router.get("/organizations/current/logo")
def get_current_organization_logo(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> Response:
    service = OrganizationService(db)
    org, _ = service.ensure_default_organization(user)
    file_bytes, content_type = service.get_branding_image(org.id, image_type="logo")
    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={"Cache-Control": "no-cache, private"},
    )


@router.get("/organizations/{org_id}/logo")
def get_organization_logo(
    org_id: str,
    db: Session = Depends(get_db),
) -> Response:
    service = OrganizationService(db)
    file_bytes, content_type = service.get_branding_image(org_id, image_type="logo")
    return Response(
        content=file_bytes,
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=3600"},
    )


@router.post("/organizations/current/logo", response_model=OrganizationRead)
async def upload_organization_logo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    file_bytes = await file.read()
    service = OrganizationService(db)
    return service.upload_branding_image(
        user, file_bytes, file.filename or "logo.png", image_type="logo"
    )


@router.post("/organizations/current/cover", response_model=OrganizationRead)
async def upload_organization_cover(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    file_bytes = await file.read()
    service = OrganizationService(db)
    return service.upload_branding_image(
        user, file_bytes, file.filename or "cover.png", image_type="cover"
    )


@router.get(
    "/organizations/current/members", response_model=list[OrganizationMemberRead]
)
def list_organization_members(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> Any:
    service = OrganizationService(db)
    return service.list_members(user)


@router.post(
    "/organizations/current/members",
    response_model=OrganizationMemberRead,
    status_code=status.HTTP_201_CREATED,
)
def invite_organization_member(
    body: OrganizationMemberInvite,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    service = OrganizationService(db)
    return service.invite_member(user, body)


@router.patch(
    "/organizations/current/members/{target_user_id}",
    response_model=OrganizationMemberRead,
)
def update_organization_member_role(
    target_user_id: str,
    body: OrganizationMemberRoleUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    service = OrganizationService(db)
    return service.update_member_role(user, target_user_id, body)


@router.delete(
    "/organizations/current/members/{target_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_organization_member(
    target_user_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> None:
    service = OrganizationService(db)
    service.remove_member(user, target_user_id)


@router.get("/cases", response_model=list[CaseRead])
def list_cases(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> Any:
    service = OrganizationService(db)
    return service.list_cases(user)


@router.post("/cases", response_model=CaseRead, status_code=status.HTTP_201_CREATED)
def create_case(
    body: CaseCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    service = OrganizationService(db)
    case_dto, _ = service.create_case(user, body)
    return case_dto


@router.get("/cases/{public_id}", response_model=CaseRead)
def get_case(
    public_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> Any:
    service = OrganizationService(db)
    return service.get_case(user, public_id)


@router.patch("/cases/{public_id}", response_model=CaseRead)
def update_case(
    public_id: str,
    body: CaseUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    service = OrganizationService(db)
    return service.update_case(user, public_id, body)


@router.get(
    "/cases/invite/{raw_token}", response_model=CandidateInviteRedemptionResponse
)
def redeem_candidate_invite(
    raw_token: str,
    db: Session = Depends(get_db),
) -> Any:
    service = OrganizationService(db)
    return service.redeem_candidate_invite(raw_token)


# Organization Forms & Schema Review Routes (Phase G2)
@router.get(
    "/organizations/current/forms", response_model=list[OrganizationFormSummary]
)
def list_organization_forms(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> Any:
    service = OrganizationFormService(db)
    return service.list_organization_forms(user)


@router.post(
    "/organizations/current/forms/upload",
    response_model=FormReviewDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_organization_form(
    file: UploadFile = File(...),
    name: str = Form(...),
    category: str = Form("general"),
    category_id: str | None = Form(None),
    submission_method: str = Form("print_and_sign"),
    instructions: str | None = Form(None),
    required_documents: str | None = Form(None),
    auto_extract: bool = Form(False),
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    pdf_bytes = await file.read()
    docs_list: list[str] = []
    if required_documents:
        try:
            parsed = json.loads(required_documents)
            if isinstance(parsed, list):
                docs_list = [str(x) for x in parsed]
        except Exception:
            docs_list = [d.strip() for d in required_documents.split(",") if d.strip()]

    service = OrganizationFormService(db)
    return service.upload_and_ingest_form(
        user=user,
        pdf_bytes=pdf_bytes,
        filename=file.filename or "form.pdf",
        name=name,
        category=category,
        category_id=category_id,
        submission_method=submission_method,
        instructions=instructions,
        required_documents=docs_list,
        auto_extract=auto_extract,
    )


@router.post(
    "/organizations/current/forms/{template_id}/auto-detect",
    response_model=FormReviewDetailResponse,
)
def auto_detect_form_fields(
    template_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    service = OrganizationFormService(db)
    return service.auto_detect_fields(user, template_id)


@router.get(
    "/organizations/current/forms/{template_id}/review",
    response_model=FormReviewDetailResponse,
)
def get_form_review(
    template_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> Any:
    service = OrganizationFormService(db)
    return service.get_form_review(user, template_id)


@router.patch(
    "/organizations/current/forms/{template_id}/review",
    response_model=FormReviewDetailResponse,
)
def update_form_review(
    template_id: str,
    body: FormReviewUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    service = OrganizationFormService(db)
    return service.update_form_review(user, template_id, body)


@router.post(
    "/organizations/current/forms/{template_id}/fields",
    response_model=FieldResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_field(
    template_id: str,
    body: FieldCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    service = OrganizationFormService(db)
    return service.add_field(user, template_id, body)


@router.patch(
    "/organizations/current/forms/{template_id}/fields/{field_id}",
    response_model=FieldResponse,
)
def update_field(
    template_id: str,
    field_id: str,
    body: FieldUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    service = OrganizationFormService(db)
    return service.update_field(user, template_id, field_id, body)


@router.delete(
    "/organizations/current/forms/{template_id}/fields/{field_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_field(
    template_id: str,
    field_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> None:
    service = OrganizationFormService(db)
    service.delete_field(user, template_id, field_id)


@router.post(
    "/organizations/current/forms/{template_id}/reorder",
    response_model=list[str],
)
@router.put(
    "/organizations/current/forms/{template_id}/fields/reorder",
    response_model=list[str],
)
@router.post(
    "/organizations/current/forms/{template_id}/fields/reorder",
    response_model=list[str],
)
def reorder_fields(
    template_id: str,
    field_ids: list[str],
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    service = OrganizationFormService(db)
    return service.reorder_fields(user, template_id, field_ids)


@router.post(
    "/organizations/current/forms/{template_id}/publish",
    response_model=FormReviewDetailResponse,
)
def publish_form(
    template_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    service = OrganizationFormService(db)
    return service.publish_form(user, template_id)


@router.post(
    "/organizations/current/forms/{template_id}/archive",
    response_model=FormReviewDetailResponse,
)
def archive_form(
    template_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    service = OrganizationFormService(db)
    return service.archive_form(user, template_id)


@router.delete(
    "/organizations/current/forms/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_organization_form(
    template_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> None:
    service = OrganizationFormService(db)
    service.delete_form_template(user, template_id)


@router.delete(
    "/organizations/current/forms/{template_id}/fields",
    response_model=FormReviewDetailResponse,
)
def clear_organization_form_fields(
    template_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    service = OrganizationFormService(db)
    return service.clear_form_fields(user, template_id)


@router.post(
    "/organizations/current/forms/translate-field",
    response_model=TranslateFieldResponse,
)
async def translate_form_field(
    body: TranslateFieldRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    service = OrganizationFormService(db)
    res = await service.translate_field_label(
        user, body.text, body.source_language, body.target_languages
    )
    return TranslateFieldResponse(translations=res)


@router.get("/organizations/current/forms/{template_id}/source-pdf")
def get_source_pdf(
    template_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> Response:
    service = OrganizationFormService(db)
    pdf_bytes, filename = service.get_source_pdf_bytes(user, template_id)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/organizations/current/forms/{template_id}/pages/{page_number}/preview")
def get_form_page_preview(
    template_id: str,
    page_number: int = 1,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> Response:
    service = OrganizationFormService(db)
    png_bytes = service.get_form_page_preview_png(user, template_id, page_number)
    return Response(content=png_bytes, media_type="image/png")


# Organization Categories & Taxonomy Routes (TYPO3-Inspired)
@router.get(
    "/organizations/current/categories",
    response_model=list[OrganizationCategoryRead],
)
def list_organization_categories(
    active_only: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> Any:
    service = OrganizationService(db)
    return service.list_categories(user, only_active=active_only)


@router.post(
    "/organizations/current/categories",
    response_model=OrganizationCategoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_organization_category(
    req: OrganizationCategoryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    service = OrganizationService(db)
    return service.create_category(user, req)


@router.put(
    "/organizations/current/categories/{category_id}",
    response_model=OrganizationCategoryRead,
)
def update_organization_category(
    category_id: str,
    req: OrganizationCategoryUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    service = OrganizationService(db)
    return service.update_category(user, category_id, req)


@router.delete(
    "/organizations/current/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_organization_category(
    category_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> None:
    service = OrganizationService(db)
    service.delete_category(user, category_id)


@router.patch(
    "/organizations/current/forms/{template_id}/category",
    response_model=OrganizationFormSummary,
)
def update_organization_form_category(
    template_id: str,
    req: FormCategoryUpdateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    service = OrganizationFormService(db)
    return service.update_form_category(user, template_id, req.category_id)


@router.post(
    "/organizations/current/forms/auto-categorize",
    response_model=dict[str, Any],
)
def auto_categorize_organization_forms(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    service = OrganizationFormService(db)
    return service.auto_categorize_forms(user)


@router.get(
    "/organizations/current/categories/{category_id}/forms",
    response_model=list[str],
)
def get_category_forms(
    category_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> Any:
    service = OrganizationService(db)
    return service.get_category_forms(user, category_id)


@router.post(
    "/organizations/current/categories/{category_id}/forms",
    response_model=list[str],
)
def assign_category_forms(
    category_id: str,
    req: CategoryFormsAssignRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    service = OrganizationService(db)
    return service.assign_category_forms(user, category_id, req.form_ids)


# Public Citizen Portals & Directory Routes (Phase G3)
@router.get("/public/organizations", response_model=list[PublicOrganizationSummary])
def list_public_organizations(
    search: str | None = None,
    type: str | None = None,
    db: Session = Depends(get_db),
) -> Any:
    service = OrganizationService(db)
    return service.list_public_organizations(search=search, organization_type=type)


@router.get("/public/organizations/{slug}", response_model=PublicOrganizationDetail)
def get_public_organization(
    slug: str,
    db: Session = Depends(get_db),
) -> Any:
    service = OrganizationService(db)
    return service.get_public_organization_by_slug(slug)


@router.get("/public/organizations/{slug}/logo")
def get_public_organization_logo(
    slug: str,
    db: Session = Depends(get_db),
) -> Response:
    service = OrganizationService(db)
    content, media_type = service.get_organization_logo_bytes(slug)
    return Response(
        content=content,
        media_type=media_type,
    )
