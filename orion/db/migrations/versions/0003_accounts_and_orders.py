"""Accounts (customers, team), login codes, refresh tokens, and the orders table

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-25
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def _id():
    return sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()"))


def _now(name: str = "created_at"):
    return sa.Column(name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


def upgrade() -> None:
    op.create_table(
        "customers",
        _id(),
        sa.Column("email", sa.Text, nullable=False, unique=True),       # stored lowercase
        sa.Column("name", sa.Text),
        sa.Column("google_sub", sa.Text, unique=True),
        sa.Column("apple_sub", sa.Text, unique=True),
        _now(),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
    )

    op.create_table(
        "team_members",
        _id(),
        sa.Column("email", sa.Text, nullable=False, unique=True),
        sa.Column("name", sa.Text),
        sa.Column("role", sa.Text, nullable=False),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        _now(),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("role in ('admin', 'agent')"),
    )

    # One-time email login codes; only an HMAC of the code is stored
    op.create_table(
        "login_codes",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("email", sa.Text, nullable=False),
        sa.Column("audience", sa.Text, nullable=False),       # customer | team
        sa.Column("code_hash", sa.Text, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        _now(),
        sa.CheckConstraint("audience in ('customer', 'team')"),
    )
    op.create_index("ix_login_codes_email", "login_codes", ["email", "audience", "created_at"])

    # Refresh tokens: only a SHA-256 of the token is stored; rotated on every use
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("token_hash", sa.Text, nullable=False, unique=True),
        sa.Column("subject_id", UUID(as_uuid=False), nullable=False),
        sa.Column("audience", sa.Text, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        _now(),
        sa.CheckConstraint("audience in ('customer', 'team')"),
    )
    op.create_index("ix_refresh_tokens_subject", "refresh_tokens", ["subject_id", "audience"])

    # Business record of each order (the agent's state lives in the checkpointer)
    op.create_table(
        "orders",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("customer_id", UUID(as_uuid=False), sa.ForeignKey("customers.id")),
        sa.Column("stage", sa.Text, nullable=False),
        sa.Column("needs_human", sa.Text),
        sa.Column("market", sa.Text),
        sa.Column("option", sa.Text),
        sa.Column("quantity", sa.Integer),
        _now(),
        _now("updated_at"),
    )
    op.create_index("ix_orders_customer", "orders", ["customer_id", "created_at"])
    op.create_index("ix_orders_needs_human", "orders", ["updated_at"], postgresql_where=sa.text("needs_human IS NOT NULL"))


def downgrade() -> None:
    op.drop_table("orders")
    op.drop_table("refresh_tokens")
    op.drop_table("login_codes")
    op.drop_table("team_members")
    op.drop_table("customers")
