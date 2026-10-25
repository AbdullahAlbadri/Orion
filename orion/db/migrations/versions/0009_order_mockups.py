"""AI mockups customers generate while ordering (illustrations only, never sent to a factory)

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-25
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "order_mockups",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_id", sa.Text, sa.ForeignKey("orders.id"), nullable=False, index=True),
        sa.Column("customer_id", UUID(as_uuid=False), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("storage_key", sa.Text, nullable=False),
        sa.Column("content_type", sa.Text, nullable=False),
        sa.Column("model", sa.Text, nullable=False),
        sa.Column("cost", sa.Numeric(10, 6)),                  # USD as reported by OpenRouter, for the stats
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("order_mockups")
