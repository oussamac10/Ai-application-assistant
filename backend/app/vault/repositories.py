from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.vault.models import UserProfileEntry


class ProfileVaultRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_for_user(self, user_id: str) -> list[UserProfileEntry]:
        stmt = (
            select(UserProfileEntry)
            .where(UserProfileEntry.user_id == user_id)
            .order_by(UserProfileEntry.question_key.asc())
        )
        return list(self.db.scalars(stmt).all())

    def get_by_key(self, user_id: str, question_key: str) -> UserProfileEntry | None:
        stmt = select(UserProfileEntry).where(
            UserProfileEntry.user_id == user_id,
            UserProfileEntry.question_key == question_key,
        )
        return self.db.scalars(stmt).first()

    def upsert(
        self,
        user_id: str,
        question_key: str,
        field_type: str,
        encrypted_payload: str,
        value_language: str,
    ) -> UserProfileEntry:
        existing = self.get_by_key(user_id, question_key)
        now = datetime.now(UTC)
        if existing:
            existing.field_type = field_type
            existing.encrypted_payload = encrypted_payload
            existing.value_language = value_language
            existing.updated_at = now
            self.db.commit()
            self.db.refresh(existing)
            return existing

        entry = UserProfileEntry(
            user_id=user_id,
            question_key=question_key,
            field_type=field_type,
            encrypted_payload=encrypted_payload,
            value_language=value_language,
        )
        self.db.add(entry)
        self.db.commit()
        self.db.refresh(entry)
        return entry

    def delete_key(self, user_id: str, question_key: str) -> bool:
        existing = self.get_by_key(user_id, question_key)
        if not existing:
            return False
        self.db.delete(existing)
        self.db.commit()
        return True

    def delete_all_for_user(self, user_id: str) -> None:
        self.db.execute(
            delete(UserProfileEntry).where(UserProfileEntry.user_id == user_id)
        )
        self.db.commit()
