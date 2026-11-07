"""add translation memories table

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-11-08 00:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f7a8b9c0d1e2"
down_revision: str | None = "e6f7a8b9c0d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "translation_memories",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("source_text_hash", sa.String(length=64), nullable=False),
        sa.Column("source_text", sa.Text(), nullable=False),
        sa.Column("source_language", sa.String(length=10), nullable=False),
        sa.Column("target_language", sa.String(length=10), nullable=False),
        sa.Column("translated_text", sa.Text(), nullable=False),
        sa.Column(
            "provider",
            sa.String(length=50),
            server_default="gemini",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "source_text_hash",
            "source_language",
            "target_language",
            name="uq_translation_memories_hash_lang",
        ),
    )
    op.create_index(
        "ix_translation_memories_hash",
        "translation_memories",
        ["source_text_hash"],
    )
    op.create_index(
        "ix_translation_memories_lookup",
        "translation_memories",
        ["source_text_hash", "source_language", "target_language"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_translation_memories_lookup", table_name="translation_memories"
    )
    op.drop_index(
        "ix_translation_memories_hash", table_name="translation_memories"
    )
    op.drop_table("translation_memories")
