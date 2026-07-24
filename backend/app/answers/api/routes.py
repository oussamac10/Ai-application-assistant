from typing import Any

from fastapi import APIRouter, Depends, Header, status
from sqlalchemy.orm import Session

from app.answers.schemas import (
    AnswerResponse,
    AnswerSubmitRequest,
    ClarificationResponse,
    ClarifySubmitRequest,
    CurrentFieldResponse,
    SummaryResponse,
)
from app.answers.services import AnswerService
from app.database.session import get_db
from app.forms.schemas import BaseSchema

router = APIRouter()


class AnswerSubmitBody(BaseSchema):
    field_id: str
    original_answer: str


def _prepare_answer_response(answer: Any) -> Any:
    if getattr(answer, "requires_clarification", False):
        unc = getattr(answer, "_uncertainties", [])
        field_type = getattr(answer.field, "field_type", "money")
        q_key = f"{field_type}_missing_{'_and_'.join(unc)}"
        answer.clarification = ClarificationResponse(missing=unc, question_key=q_key)
    return answer


@router.get(
    "/form-sessions/{session_id}/current-field",
    response_model=CurrentFieldResponse,
)
def get_current_field(
    session_id: str,
    x_session_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Any:
    service = AnswerService(db)
    return service.get_current_field(session_id, x_session_token)


@router.post(
    "/form-sessions/{session_id}/answers",
    response_model=AnswerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def submit_answer(
    session_id: str,
    data: AnswerSubmitBody,
    x_session_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Any:
    service = AnswerService(db)
    ans = await service.submit_answer(
        session_id, data.field_id, data.original_answer, x_session_token
    )
    return _prepare_answer_response(ans)


@router.post(
    "/form-sessions/{session_id}/answers/{answer_id}/clarify",
    response_model=AnswerResponse,
)
def submit_clarification(
    session_id: str,
    answer_id: str,
    data: ClarifySubmitRequest,
    x_session_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Any:
    service = AnswerService(db)
    ans = service.submit_clarification(
        session_id, answer_id, data.values, x_session_token
    )
    return _prepare_answer_response(ans)


@router.post(
    "/form-sessions/{session_id}/answers/{answer_id}/confirm",
    response_model=AnswerResponse,
)
def confirm_answer(
    session_id: str,
    answer_id: str,
    x_session_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Any:
    service = AnswerService(db)
    return service.confirm_answer(session_id, answer_id, x_session_token)


@router.put(
    "/form-sessions/{session_id}/fields/{field_id}/answer",
    response_model=AnswerResponse,
)
async def change_answer(
    session_id: str,
    field_id: str,
    data: AnswerSubmitRequest,
    x_session_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Any:
    service = AnswerService(db)
    ans = await service.submit_answer(
        session_id, field_id, data.original_answer, x_session_token
    )
    return _prepare_answer_response(ans)


@router.post(
    "/form-sessions/{session_id}/previous-field",
    response_model=CurrentFieldResponse,
)
def previous_field(
    session_id: str,
    x_session_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Any:
    service = AnswerService(db)
    return service.previous_field(session_id, x_session_token)


@router.get("/form-sessions/{session_id}/summary", response_model=SummaryResponse)
def get_summary(
    session_id: str,
    x_session_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Any:
    service = AnswerService(db)
    fields_list = service.get_summary(session_id, x_session_token)
    return {"fields": fields_list}


@router.post("/form-sessions/{session_id}/confirm-summary")
def confirm_summary(
    session_id: str,
    x_session_token: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Any:
    service = AnswerService(db)
    service.confirm_summary(session_id, x_session_token)
    return {"status": "ready_for_export"}
