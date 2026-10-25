"""Product ideas generated from the business profile, kept until the profile changes

Revision ID: 0006
Revises: 0005
Create Date: 2026-10-25
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customer_suggestions",
        sa.Column("customer_id", UUID(as_uuid=False), sa.ForeignKey("customers.id"), primary_key=True),
        sa.Column("lang", sa.Text, primary_key=True),
        sa.Column("fingerprint", sa.Text, nullable=False),   # inputs they were made from (profile, products, prompt)
        sa.Column("items", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("customer_suggestions")
