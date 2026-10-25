from __future__ import annotations

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_optional
from app.auth.models import User
from app.database.session import get_db
from app.jobs.schemas import JobStatusResponse
from app.jobs.service import ProcessingJobService

router = APIRouter(tags=["jobs"])


@router.get(
    "/jobs/{job_id}",
    response_model=JobStatusResponse,
    status_code=status.HTTP_200_OK,
)
def get_job_status(
    job_id: str,
    x_document_token: str | None = Header(default=None, alias="X-Document-Token"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> JobStatusResponse:
    service = ProcessingJobService(
        db, current_user_id=current_user.id if current_user else None
    )
    return service.get_job_status(job_id, x_document_token)
