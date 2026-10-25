"""What a recorded manufacturer price is for: the product, a sample, shipping, or something else

Revision ID: 0008
Revises: 0007
Create Date: 2026-10-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("price_records", sa.Column("charge", sa.Text, nullable=False, server_default="product"))
    op.create_check_constraint(
        "ck_price_records_charge", "price_records", "charge in ('product', 'sample', 'shipping', 'other')"
    )


def downgrade() -> None:
    op.drop_constraint("ck_price_records_charge", "price_records")
    op.drop_column("price_records", "charge")
