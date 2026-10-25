from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_admin, verify_csrf
from app.core.config import settings
from app.database.session import get_db
from app.questions.repositories import QuestionRepository
from app.questions.schemas import (
    QuestionTranslationCreate,
    QuestionTranslationResponse,
)
from app.questions.services import QuestionCatalogService, QuestionReviewService

router = APIRouter()


def verify_admin_api_enabled() -> None:
    if not settings.QUESTION_ADMIN_API_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin API is disabled.",
        )


@router.get(
    "/questions",
    response_model=list[QuestionTranslationResponse],
    dependencies=[Depends(verify_admin_api_enabled), Depends(require_admin)],
)
def list_questions(
    question_key: str | None = Query(default=None, alias="questionKey"),
    language: str | None = None,
    review_status: str | None = Query(default=None, alias="reviewStatus"),
    source: str | None = None,
    db: Session = Depends(get_db),
) -> Any:
    """List and filter catalog questions (admin only)."""
    repo = QuestionRepository(db)
    return repo.list_questions(
        question_key=question_key,
        language=language,
        review_status=review_status,
        source=source,
    )


@router.post(
    "/questions/{question_key}/translations",
    response_model=QuestionTranslationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(verify_admin_api_enabled),
        Depends(require_admin),
        Depends(verify_csrf),
    ],
)
def create_manual_translation(
    question_key: str,
    language: str,
    data: QuestionTranslationCreate,
    db: Session = Depends(get_db),
) -> Any:
    """Create or update a manually approved translation for a semantic key."""
    service = QuestionCatalogService(db)
    return service.create_manual_translation(
        question_key=question_key,
        language=language,
        text=data.text,
        help_text=data.help_text,
        placeholder=data.placeholder,
    )


@router.post(
    "/questions/{question_key}/translations/{language}/approve",
    response_model=QuestionTranslationResponse,
    dependencies=[
        Depends(verify_admin_api_enabled),
        Depends(require_admin),
        Depends(verify_csrf),
    ],
)
def approve_translation(
    question_key: str,
    language: str,
    db: Session = Depends(get_db),
) -> Any:
    """Approve a pending translation (admin only)."""
    service = QuestionReviewService(db)
    return service.approve_translation(question_key, language)


@router.post(
    "/questions/{question_key}/translations/{language}/reject",
    response_model=QuestionTranslationResponse,
    dependencies=[
        Depends(verify_admin_api_enabled),
        Depends(require_admin),
        Depends(verify_csrf),
    ],
)
def reject_translation(
    question_key: str,
    language: str,
    db: Session = Depends(get_db),
) -> Any:
    """Reject a pending translation (admin only)."""
    service = QuestionReviewService(db)
    return service.reject_translation(question_key, language)
