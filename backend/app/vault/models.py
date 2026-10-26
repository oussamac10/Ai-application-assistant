import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class UserProfileEntry(Base):
    """Encrypted reusable personal profile entry (`Phase S2-02`).

    Plaintext applicant values are NEVER stored in PostgreSQL; only the
    Fernet-encrypted JSON payload (`encrypted_payload`) is persisted.
    """

    __tablename__ = "user_profile_entries"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    field_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="string",
    )
    encrypted_payload: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    value_language: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="en",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "question_key",
            name="uq_user_profile_entries_user_question_key",
        ),
    )
