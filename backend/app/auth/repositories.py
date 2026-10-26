from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.models import AuthActionToken, AuthSession, User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_user(
        self,
        email: str,
        normalized_email: str,
        password_hash: str,
        role: str = "user",
    ) -> User:
        user = User(
            email=email,
            normalized_email=normalized_email,
            password_hash=password_hash,
            role=role,
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

    def mark_email_verified(self, user: User, now: datetime) -> User:
        if user.email_verified_at is None:
            user.email_verified_at = now
            self.db.commit()
            self.db.refresh(user)
        return user

    def update_password_hash(self, user: User, password_hash: str) -> User:
        user.password_hash = password_hash
        self.db.commit()
        self.db.refresh(user)
        return user

    def hard_delete(self, user: User) -> None:
        self.db.delete(user)
        self.db.commit()


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


class AuthActionTokenRepository:
    def __init__(self, db: Session):
        self.db = db

    def invalidate_pending_for_user(
        self, user_id: str, purpose: str, now: datetime
    ) -> None:
        stmt = select(AuthActionToken).where(
            AuthActionToken.user_id == user_id,
            AuthActionToken.purpose == purpose,
            AuthActionToken.consumed_at.is_(None),
        )
        for row in self.db.scalars(stmt).all():
            row.consumed_at = now
        self.db.flush()

    def create_token(
        self,
        user_id: str,
        purpose: str,
        token_hash: str,
        expires_at: datetime,
    ) -> AuthActionToken:
        row = AuthActionToken(
            user_id=user_id,
            purpose=purpose,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def get_by_token_hash(self, token_hash: str) -> AuthActionToken | None:
        stmt = select(AuthActionToken).where(AuthActionToken.token_hash == token_hash)
        return self.db.scalars(stmt).first()

    def consume(self, token_row: AuthActionToken, now: datetime) -> None:
        token_row.consumed_at = now
        self.db.commit()
