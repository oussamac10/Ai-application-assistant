from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import require_user, verify_csrf
from app.auth.models import User
from app.database.session import get_db
from app.vault.schemas import (
    PrefillSessionFromVaultResponse,
    ProfileVaultEntryResponse,
    ProfileVaultUpsertRequest,
    SaveSessionToVaultResponse,
)
from app.vault.services import ProfileVaultService

router = APIRouter(tags=["profile-vault"])


@router.get("/profile-vault", response_model=list[ProfileVaultEntryResponse])
def list_profile_vault(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
) -> Any:
    return ProfileVaultService(db).list_entries(user.id)


@router.put(
    "/profile-vault/{question_key}",
    response_model=ProfileVaultEntryResponse,
)
def upsert_profile_vault_entry(
    question_key: str,
    body: ProfileVaultUpsertRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    return ProfileVaultService(db).upsert_entry(
        user_id=user.id,
        question_key=question_key,
        value=body.value,
        field_type=body.field_type,
        value_language=body.value_language,
    )


@router.delete(
    "/profile-vault/{question_key}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_profile_vault_entry(
    question_key: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> None:
    ProfileVaultService(db).delete_entry(user.id, question_key)


@router.delete(
    "/profile-vault",
    status_code=status.HTTP_204_NO_CONTENT,
)
def clear_profile_vault(
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> None:
    ProfileVaultService(db).clear_vault(user.id)


@router.post(
    "/form-sessions/{session_id}/save-to-vault",
    response_model=SaveSessionToVaultResponse,
)
def save_session_to_vault(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    return ProfileVaultService(db).save_session_answers_to_vault(user.id, session_id)


@router.post(
    "/form-sessions/{session_id}/prefill-from-vault",
    response_model=PrefillSessionFromVaultResponse,
)
def prefill_session_from_vault(
    session_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(require_user),
    _csrf: None = Depends(verify_csrf),
) -> Any:
    return ProfileVaultService(db).prefill_session_from_vault(user.id, session_id)
