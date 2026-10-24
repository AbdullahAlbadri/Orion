"""Manufacturers, ranked product lists, message log and the append-only price dataset

Revision ID: 0001
Revises:
Create Date: 2026-10-24
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "manufacturers",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("name", sa.Text, nullable=False),
        sa.Column("contact", sa.Text),
        sa.Column("channel", sa.Text, nullable=False, server_default="manual_relay"),
        sa.Column("language", sa.Text, nullable=False, server_default="zh"),
        sa.Column("active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Ordered manufacturer list per product type; option NULL = any option in the market
    op.create_table(
        "manufacturer_products",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("manufacturer_id", sa.Text, sa.ForeignKey("manufacturers.id"), nullable=False),
        sa.Column("market", sa.Text, nullable=False),
        sa.Column("option", sa.Text),
        sa.Column("rank", sa.Integer, nullable=False),
        sa.UniqueConstraint("manufacturer_id", "market", "option", postgresql_nulls_not_distinct=True),
    )

    # Every message to/from manufacturers: outbox for the manual relay, and the audit trail
    op.create_table(
        "manufacturer_messages",
        sa.Column("id", sa.Text, primary_key=True),
        sa.Column("order_id", sa.Text, nullable=False, index=True),
        sa.Column("manufacturer_id", sa.Text, sa.ForeignKey("manufacturers.id"), nullable=False),
        sa.Column("direction", sa.Text, nullable=False),     # out | in
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False),        # pending_send | sent | blocked | received
        sa.Column("blocked_reason", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("direction in ('out', 'in')"),
        sa.CheckConstraint("status in ('pending_send', 'sent', 'blocked', 'received')"),
    )

    op.create_table(
        "price_records",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("source_key", sa.Text, nullable=False, unique=True),
        sa.Column("manufacturer_id", sa.Text, sa.ForeignKey("manufacturers.id"), nullable=False),
        sa.Column("order_id", sa.Text),
        sa.Column("market", sa.Text, nullable=False),
        sa.Column("option", sa.Text, nullable=False),
        sa.Column("attributes", JSONB, nullable=False),
        sa.Column("quantity", sa.Integer),
        sa.Column("unit_price", sa.Numeric(14, 4), nullable=False),
        sa.Column("currency", sa.Text),
        sa.Column("unit", sa.Text, nullable=False),
        sa.Column("incoterm", sa.Text),
        sa.Column("shipping_included", sa.Boolean),
        sa.Column("tax_included", sa.Boolean),
        sa.Column("source", sa.Text, nullable=False),          # order | weekly_check
        sa.Column("source_message_id", sa.Text, nullable=False),
        sa.Column("quoted_text", sa.Text, nullable=False),
        sa.Column("original_text", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False),          # verified | extracted | disputed
        sa.Column("problems", JSONB, nullable=False, server_default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status in ('verified', 'extracted', 'disputed')"),
        sa.CheckConstraint("source in ('order', 'weekly_check')"),
    )
    op.create_index("ix_price_records_lookup", "price_records", ["manufacturer_id", "market", "option", "created_at"])

    # Append-only: corrections are new rows, never edits
    op.execute("""
        CREATE FUNCTION price_records_append_only() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'price_records is append-only';
        END;
        $$ LANGUAGE plpgsql;
    """)
    op.execute("""
        CREATE TRIGGER price_records_no_update_delete
        BEFORE UPDATE OR DELETE ON price_records
        FOR EACH ROW EXECUTE FUNCTION price_records_append_only();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS price_records_no_update_delete ON price_records")
    op.execute("DROP FUNCTION IF EXISTS price_records_append_only()")
    op.drop_table("price_records")
    op.drop_table("manufacturer_messages")
    op.drop_table("manufacturer_products")
    op.drop_table("manufacturers")
