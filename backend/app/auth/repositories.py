from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import AuthSession, User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_user(
        self, email: str, normalized_email: str, password_hash: str
    ) -> User:
        user = User(
            email=email,
            normalized_email=normalized_email,
            password_hash=password_hash,
            status="active",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_by_normalized_email(self, normalized_email: str) -> User | None:
        stmt = select(User).where(User.normalized_email == normalized_email)
        return self.db.scalars(stmt).first()

    def get_by_id(self, user_id: str) -> User | None:
        return self.db.get(User, user_id)


class AuthSessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_session(
        self, user_id: str, token_hash: str, expires_at: datetime
    ) -> AuthSession:
        session = AuthSession(
            user_id=user_id, token_hash=token_hash, expires_at=expires_at
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get_by_token_hash(self, token_hash: str) -> AuthSession | None:
        stmt = select(AuthSession).where(AuthSession.token_hash == token_hash)
        return self.db.scalars(stmt).first()

    def revoke(self, session: AuthSession, now: datetime) -> None:
        session.revoked_at = now
        self.db.commit()

    def touch_last_used(self, session: AuthSession, now: datetime) -> None:
        session.last_used_at = now
        self.db.commit()

    def revoke_all_for_user(self, user_id: str, now: datetime) -> None:
        stmt = select(AuthSession).where(
            AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None)
        )
        for session in self.db.scalars(stmt).all():
            session.revoked_at = now
        self.db.commit()
