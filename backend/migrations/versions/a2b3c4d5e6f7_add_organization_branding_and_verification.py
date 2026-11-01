"""add organization branding and verification phase g1

Revision ID: a2b3c4d5e6f7
Revises: f6a7b8c9d0e1
Create Date: 2026-11-01 02:25:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a2b3c4d5e6f7"
down_revision: str | None = "f6a7b8c9d0e1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column(
            "verification_status",
            sa.String(length=30),
            nullable=False,
            server_default="unverified",
        ),
    )
    op.add_column(
        "organizations",
        sa.Column(
            "is_verified_government",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "organizations",
        sa.Column("verification_details", sa.JSON(), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("description", sa.Text(), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("logo_storage_path", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("cover_image_storage_path", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("office_address", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("contact_email", sa.String(length=320), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column("official_website_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "organizations",
        sa.Column(
            "supported_languages",
            sa.JSON(),
            nullable=False,
            server_default='["de", "en"]',
        ),
    )


def downgrade() -> None:
    op.drop_column("organizations", "supported_languages")
    op.drop_column("organizations", "official_website_url")
    op.drop_column("organizations", "contact_phone")
    op.drop_column("organizations", "contact_email")
    op.drop_column("organizations", "office_address")
    op.drop_column("organizations", "cover_image_storage_path")
    op.drop_column("organizations", "logo_storage_path")
    op.drop_column("organizations", "description")
    op.drop_column("organizations", "verification_details")
    op.drop_column("organizations", "is_verified_government")
    op.drop_column("organizations", "verification_status")
