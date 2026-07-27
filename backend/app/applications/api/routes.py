from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.applications.schemas import (
    ApplicationDetail,
    ApplicationSummary,
    ClaimApplicationRequest,
    RenameApplicationRequest,
)
from app.applications.services import ApplicationService
from app.auth.dependencies import require_user, verify_csrf
from app.auth.models import User
from app.database.session import get_db

router = APIRouter(prefix="/applications", tags=["applications"])


@router.get("", response_model=list[ApplicationSummary])
def list_applications(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> Any:
    service = ApplicationService(db)
    return service.list_applications(user.id)


@router.get("/{application_id}", response_model=ApplicationDetail)
def get_application(
    application_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> Any:
    service = ApplicationService(db)
    return service.get_application(user.id, application_id)


@router.patch("/{application_id}", response_model=ApplicationSummary)
def rename_application(
    application_id: str,
    body: RenameApplicationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    service = ApplicationService(db)
    return service.rename_application(user.id, application_id, body.title)


@router.delete("/{application_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_application(
    application_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> None:
    service = ApplicationService(db)
    service.delete_application(user.id, application_id)


@router.post("/claim", response_model=ApplicationDetail)
def claim_application(
    body: ClaimApplicationRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    service = ApplicationService(db)
    service.claim(
        user.id,
        body.session_id,
        body.session_token,
        body.document_id,
        body.document_token,
    )
    return service.get_application(user.id, body.session_id)
