from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_user, verify_csrf
from app.auth.models import User
from app.database.session import get_db
from app.organizations.schemas import (
    CandidateInviteRedemptionResponse,
    CaseCreateRequest,
    CaseRead,
    CaseUpdateRequest,
    OrganizationRead,
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
