"""Translation Memory ORM models.

Stores cross-form and cross-organization reusable translations for administrative
form labels and instructions.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


def hash_text(text: str) -> str:
    """Computes a canonical SHA-256 hash of normalized text."""
    normalized = text.strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class TranslationMemory(Base):
    __tablename__ = "translation_memories"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source_text_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_language: Mapped[str] = mapped_column(String(10), nullable=False)
    target_language: Mapped[str] = mapped_column(String(10), nullable=False)
    translated_text: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False, default="gemini")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "source_text_hash",
            "source_language",
            "target_language",
            name="uq_translation_memories_hash_lang",
        ),
        Index("ix_translation_memories_hash", "source_text_hash"),
        Index(
            "ix_translation_memories_lookup",
            "source_text_hash",
            "source_language",
            "target_language",
        ),
    )
