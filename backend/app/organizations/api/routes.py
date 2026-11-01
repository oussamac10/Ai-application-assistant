from typing import Any

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_user, verify_csrf
from app.auth.models import User
from app.database.session import get_db
from app.organizations.schemas import (
    CandidateInviteRedemptionResponse,
    CaseCreateRequest,
    CaseRead,
    CaseUpdateRequest,
    OrganizationCreateRequest,
    OrganizationMemberInvite,
    OrganizationMemberRead,
    OrganizationMemberRoleUpdate,
    OrganizationProfileUpdate,
    OrganizationRead,
    OrganizationVerificationRequest,
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


@router.post("/organizations", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
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
