"""Customer settings, business profile and addresses, products, stage history, notifications, support requests

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-25
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def _now(name: str = "created_at"):
    return sa.Column(name, sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now())


def _customer():
    return sa.Column("customer_id", UUID(as_uuid=False), sa.ForeignKey("customers.id"), nullable=False)


def upgrade() -> None:
    # Account preferences (Settings page)
    op.add_column("customers", sa.Column("phone", sa.Text))
    op.add_column("customers", sa.Column("lang", sa.Text, nullable=False, server_default="ar"))
    op.add_column("customers", sa.Column("calendar", sa.Text, nullable=False, server_default="gregorian"))
    op.add_column("customers", sa.Column("currency", sa.Text, nullable=False, server_default="SAR"))
    op.add_column("customers", sa.Column("notify", JSONB, nullable=False, server_default="{}"))
    op.add_column("customers", sa.Column("onboarded_at", sa.DateTime(timezone=True)))

    # What the business is (the AI reads name, type and description at the start of every order)
    op.create_table(
        "business_profiles",
        sa.Column("customer_id", UUID(as_uuid=False), sa.ForeignKey("customers.id"), primary_key=True),
        sa.Column("name", sa.Text),
        sa.Column("business_type", sa.Text),
        sa.Column("store_platform", sa.Text),
        sa.Column("store_url", sa.Text),
        sa.Column("description", sa.Text),
        sa.Column("contacts", JSONB, nullable=False, server_default="[]"),   # authorised people: name, phone, role
        _now("updated_at"),
    )

    op.create_table(
        "addresses",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        _customer(),
        sa.Column("label", sa.Text),
        sa.Column("contact_name", sa.Text, nullable=False),
        sa.Column("phone", sa.Text, nullable=False),
        sa.Column("city", sa.Text, nullable=False),
        sa.Column("district", sa.Text),
        sa.Column("street", sa.Text, nullable=False),
        sa.Column("building", sa.Text),
        sa.Column("postal_code", sa.Text),
        sa.Column("notes", sa.Text),
        sa.Column("is_default", sa.Boolean, nullable=False, server_default=sa.false()),
        _now(),
        _now("updated_at"),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),   # kept for orders that already used it
    )
    op.create_index("ix_addresses_customer", "addresses", ["customer_id"])
    op.create_index(
        "ux_addresses_default", "addresses", ["customer_id"], unique=True,
        postgresql_where=sa.text("is_default AND deleted_at IS NULL"),
    )

    # A product is saved when its first order's summary is confirmed; reorders point back to it
    op.create_table(
        "products",
        sa.Column("id", sa.Text, primary_key=True),             # id of the order that created it
        _customer(),
        sa.Column("market", sa.Text, nullable=False),
        sa.Column("option", sa.Text, nullable=False),
        sa.Column("notes", sa.Text),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        _now(),
    )
    op.add_column("orders", sa.Column("product_id", sa.Text, sa.ForeignKey("products.id")))
    op.add_column("orders", sa.Column("reorder_of", sa.Text))
    op.add_column("orders", sa.Column("revisions", sa.Integer, nullable=False, server_default="0"))
    op.add_column("orders", sa.Column("mismatches_caught", sa.Integer, nullable=False, server_default="0"))

    # Every stage change and who the order was then waiting on (stats; cannot be rebuilt later)
    op.create_table(
        "order_stage_events",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("order_id", sa.Text, sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("stage", sa.Text, nullable=False),
        sa.Column("waiting_on", sa.Text),     # customer | factory | orion | shipping | NULL (closed)
        sa.Column("at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_order_stage_events_order", "order_stage_events", ["order_id", "at"])

    # Customer-facing updates (Messages page, header bell)
    op.create_table(
        "notifications",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        _customer(),
        sa.Column("order_id", sa.Text),
        sa.Column("kind", sa.Text, nullable=False),          # status | team
        sa.Column("event", sa.Text),                         # stage name, or the support request id
        sa.Column("title_en", sa.Text, nullable=False),
        sa.Column("title_ar", sa.Text, nullable=False),
        sa.Column("body_en", sa.Text),
        sa.Column("body_ar", sa.Text),
        sa.Column("href", sa.Text),
        sa.Column("emailed", sa.Boolean, nullable=False, server_default=sa.false()),
        _now(),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("kind in ('status', 'team')"),
    )
    op.create_index("ix_notifications_customer", "notifications", ["customer_id", "created_at"])

    # Help requests: every one is an item in the team console
    op.create_table(
        "support_requests",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ref", sa.BigInteger, sa.Identity(start=1001), nullable=False, unique=True),
        _customer(),
        sa.Column("order_id", sa.Text, sa.ForeignKey("orders.id")),
        sa.Column("topic", sa.Text, nullable=False),
        sa.Column("status", sa.Text, nullable=False, server_default="open"),
        sa.Column("context", JSONB, nullable=False, server_default="{}"),   # order stage, spec version when opened
        _now(),
        _now("updated_at"),
        sa.CheckConstraint("topic in ('order', 'change', 'price', 'delivery', 'account', 'other')"),
        sa.CheckConstraint("status in ('open', 'waiting_customer', 'resolved')"),
    )
    op.create_index("ix_support_requests_customer", "support_requests", ["customer_id", "updated_at"])
    op.create_table(
        "support_messages",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("request_id", UUID(as_uuid=False), sa.ForeignKey("support_requests.id"), nullable=False),
        sa.Column("author", sa.Text, nullable=False),        # customer | team
        sa.Column("author_email", sa.Text),                  # team member, for the console
        sa.Column("body", sa.Text, nullable=False),
        _now(),
        sa.CheckConstraint("author in ('customer', 'team')"),
    )
    op.create_index("ix_support_messages_request", "support_messages", ["request_id", "created_at"])


def downgrade() -> None:
    op.drop_table("support_messages")
    op.drop_table("support_requests")
    op.drop_table("notifications")
    op.drop_table("order_stage_events")
    for column in ("mismatches_caught", "revisions", "reorder_of", "product_id"):
        op.drop_column("orders", column)
    op.drop_table("products")
    op.drop_table("addresses")
    op.drop_table("business_profiles")
    for column in ("onboarded_at", "notify", "currency", "calendar", "lang", "phone"):
        op.drop_column("customers", column)
