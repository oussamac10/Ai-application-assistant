"""add subscriptions and ai usage events phase s4

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-11-01 01:45:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f6a7b8c9d0e1"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Organization Subscriptions
    op.create_table(
        "organization_subscriptions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("stripe_customer_id", sa.String(length=100), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(length=100), nullable=True),
        sa.Column(
            "plan_key",
            sa.String(length=50),
            nullable=False,
            server_default="agency_sandbox",
        ),
        sa.Column(
            "status",
            sa.String(length=30),
            nullable=False,
            server_default="active",
        ),
        sa.Column(
            "monthly_case_limit",
            sa.Integer(),
            nullable=False,
            server_default="3",
        ),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "cancel_at_period_end",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
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
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", name="uq_org_subscriptions_org_id"
        ),
    )
    op.create_index(
        "ix_org_subscriptions_org_id",
        "organization_subscriptions",
        ["organization_id"],
    )
    op.create_index(
        "ix_org_subscriptions_stripe_customer",
        "organization_subscriptions",
        ["stripe_customer_id"],
    )
    op.create_index(
        "ix_org_subscriptions_stripe_sub",
        "organization_subscriptions",
        ["stripe_subscription_id"],
    )

    # 2. AI Usage Events
    op.create_table(
        "ai_usage_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=True),
        sa.Column("case_id", sa.String(length=36), nullable=True),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("operation", sa.String(length=50), nullable=False),
        sa.Column(
            "prompt_tokens",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "completion_tokens",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "cost_eur",
            sa.Float(),
            nullable=False,
            server_default="0.0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["case_id"],
            ["organization_cases.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["form_sessions.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_usage_events_org_id",
        "ai_usage_events",
        ["organization_id"],
    )
    op.create_index(
        "ix_ai_usage_events_case_id",
        "ai_usage_events",
        ["case_id"],
    )
    op.create_index(
        "ix_ai_usage_events_session_id",
        "ai_usage_events",
        ["session_id"],
    )
    op.create_index(
        "ix_ai_usage_events_created_at",
        "ai_usage_events",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_table("ai_usage_events")
    op.drop_table("organization_subscriptions")
