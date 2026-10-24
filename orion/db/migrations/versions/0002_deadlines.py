"""Deadlines: time-based events (manufacturer timeout, quote expiry) fired by the worker

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "deadlines",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("order_id", sa.Text, nullable=False),
        sa.Column("kind", sa.Text, nullable=False),          # manufacturer_reply | quote_expiry
        sa.Column("ref", sa.Text, nullable=False),           # manufacturer id, quote id...
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="pending"),
        # Bumped on every (re)schedule; part of the timeout event id, so retries of one firing dedupe
        sa.Column("generation", sa.Integer, nullable=False, server_default="1"),
        sa.Column("tries", sa.Integer, nullable=False, server_default="0"),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("fired_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("order_id", "kind", "ref"),
        sa.CheckConstraint("status in ('pending', 'firing', 'fired', 'skipped', 'cancelled', 'failed')"),
    )
    # The worker's query: pending rows that are due
    op.create_index(
        "ix_deadlines_due", "deadlines", ["due_at"], postgresql_where=sa.text("status = 'pending'")
    )


def downgrade() -> None:
    op.drop_table("deadlines")
