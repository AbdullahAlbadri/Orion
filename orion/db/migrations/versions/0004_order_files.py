"""Files customers upload to an order (logos, artwork)

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-25
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "order_files",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_id", sa.Text, sa.ForeignKey("orders.id"), nullable=False, index=True),
        sa.Column("customer_id", UUID(as_uuid=False), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("name", sa.Text, nullable=False),               # original file name, shown only
        sa.Column("content_type", sa.Text, nullable=False),       # sniffed from the bytes
        sa.Column("size", sa.Integer, nullable=False),
        sa.Column("storage_key", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("order_files")
