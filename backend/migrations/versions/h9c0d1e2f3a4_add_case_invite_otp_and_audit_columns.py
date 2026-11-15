"""add case invite otp and audit columns

Revision ID: h9c0d1e2f3a4
Revises: g8b9c0d1e2f3
Create Date: 2026-11-15 14:05:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "h9c0d1e2f3a4"
down_revision: str | None = "g8b9c0d1e2f3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "organization_cases",
        sa.Column("otp_code_hash", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "organization_cases",
        sa.Column("otp_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organization_cases",
        sa.Column(
            "otp_attempts",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "organization_cases",
        sa.Column("otp_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organization_cases",
        sa.Column("last_accessed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organization_cases",
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organization_cases",
        sa.Column(
            "resend_count",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
    )
    op.add_column(
        "organization_cases",
        sa.Column("last_resent_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "organization_cases",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("organization_cases", "completed_at")
    op.drop_column("organization_cases", "last_resent_at")
    op.drop_column("organization_cases", "resend_count")
    op.drop_column("organization_cases", "revoked_at")
    op.drop_column("organization_cases", "last_accessed_at")
    op.drop_column("organization_cases", "otp_verified_at")
    op.drop_column("organization_cases", "otp_attempts")
    op.drop_column("organization_cases", "otp_expires_at")
    op.drop_column("organization_cases", "otp_code_hash")
