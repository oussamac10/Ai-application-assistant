"""add index to provider_usage_records user_id

Revision ID: g8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-11-08 00:55:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "g8b9c0d1e2f3"
down_revision: str | None = "f7a8b9c0d1e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_provider_usage_records_user_id",
        "provider_usage_records",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_provider_usage_records_user_id",
        table_name="provider_usage_records",
    )
