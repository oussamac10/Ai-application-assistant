"""add user_profile_entries table phase s2

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-10-26 21:23:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "c3d4e5f6a7b8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "user_profile_entries",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("question_key", sa.String(length=100), nullable=False),
        sa.Column("field_type", sa.String(length=50), nullable=False),
        sa.Column("encrypted_payload", sa.Text(), nullable=False),
        sa.Column("value_language", sa.String(length=10), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "question_key",
            name="uq_user_profile_entries_user_question_key",
        ),
    )
    op.create_index(
        "ix_user_profile_entries_id", "user_profile_entries", ["id"], unique=False
    )
    op.create_index(
        "ix_user_profile_entries_user_id",
        "user_profile_entries",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_user_profile_entries_question_key",
        "user_profile_entries",
        ["question_key"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_profile_entries_question_key", table_name="user_profile_entries"
    )
    op.drop_index("ix_user_profile_entries_user_id", table_name="user_profile_entries")
    op.drop_index("ix_user_profile_entries_id", table_name="user_profile_entries")
    op.drop_table("user_profile_entries")
