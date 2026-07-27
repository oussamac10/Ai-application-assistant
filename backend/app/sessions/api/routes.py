from typing import Any

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user_optional
from app.auth.models import User
from app.database.session import get_db
from app.sessions.models import FormSession
from app.sessions.schemas import (
    SessionCreate,
    SessionCreateResponse,
    SessionResponse,
)
from app.sessions.services import SessionService

router = APIRouter()


@router.post(
    "/form-versions/{version_id}/sessions",
    response_model=SessionCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_session(
    version_id: str,
    data: SessionCreate,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> Any:
    service = SessionService(db)
    session, token = service.create_session(
        form_version_id=version_id,
        user_language=data.user_language,
        output_language=data.output_language,
        current_user_id=current_user.id if current_user else None,
    )
    # Set dynamic property for the Pydantic response serializer
    session.ownership_token = token  # type: ignore[attr-defined]
    return session


@router.get("/form-sessions/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: str,
    x_session_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> FormSession:
    service = SessionService(db)
    return service.get_session(
        session_id, x_session_token, current_user.id if current_user else None
    )


@router.post("/form-sessions/{session_id}/start", response_model=SessionResponse)
def start_session(
    session_id: str,
    x_session_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> FormSession:
    service = SessionService(db)
    return service.start_session(
        session_id, x_session_token, current_user.id if current_user else None
    )


@router.post("/form-sessions/{session_id}/cancel", response_model=SessionResponse)
def cancel_session(
    session_id: str,
    x_session_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
) -> FormSession:
    service = SessionService(db)
    return service.cancel_session(
        session_id, x_session_token, current_user.id if current_user else None
    )
