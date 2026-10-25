"""Brand kit on the business profile: saved logos and brand colours, suggested in every new order

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-25
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # [{hex: "#FEB72F", name: "Gold"}]; the order form offers them on colour questions
    op.add_column("business_profiles", sa.Column("brand_colors", JSONB, nullable=False, server_default="[]"))

    # Logos kept on the profile. Using one in an order adds an order_files row pointing at the same stored bytes.
    op.create_table(
        "business_files",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("customer_id", UUID(as_uuid=False), sa.ForeignKey("customers.id"), nullable=False, index=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("content_type", sa.Text, nullable=False),   # sniffed from the bytes
        sa.Column("size", sa.Integer, nullable=False),
        sa.Column("storage_key", sa.Text, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("business_files")
    op.drop_column("business_profiles", "brand_colors")
