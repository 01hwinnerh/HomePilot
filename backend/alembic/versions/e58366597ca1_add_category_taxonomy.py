"""Add category taxonomy.

Revision ID: e58366597ca1
Revises: 20260809_0003
Create Date: 2026-08-10 16:20:44.138792
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op
from app.shared.models.utc_datetime import UTCDateTime

revision: str = "e58366597ca1"
down_revision: str | Sequence[str] | None = "20260809_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", UTCDateTime(), nullable=False),
        sa.Column("updated_at", UTCDateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["parent_id"],
            ["categories.id"],
            name=op.f("fk_categories_parent_id_categories"),
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("slug", name="uq_categories_slug"),
    )
    op.create_index(op.f("ix_categories_parent_id"), "categories", ["parent_id"], unique=False)

    now = datetime.now(UTC)
    categories = sa.table(
        "categories",
        sa.column("id", sa.Integer()),
        sa.column("parent_id", sa.Integer()),
        sa.column("slug", sa.String()),
        sa.column("name", sa.String()),
        sa.column("sort_order", sa.Integer()),
        sa.column("is_active", sa.Boolean()),
        sa.column("created_at", UTCDateTime()),
        sa.column("updated_at", UTCDateTime()),
    )
    op.bulk_insert(
        categories,
        [
            {
                "id": 1,
                "parent_id": None,
                "slug": "other-home",
                "name": "Other Home",
                "sort_order": 999,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
            }
        ],
    )

    op.add_column("products", sa.Column("category_id", sa.Integer(), nullable=True))
    op.execute(sa.text("UPDATE products SET category_id = 1 WHERE category_id IS NULL"))
    op.alter_column("products", "category_id", existing_type=sa.Integer(), nullable=False)
    op.create_index(op.f("ix_products_category_id"), "products", ["category_id"], unique=False)
    op.create_foreign_key(
        op.f("fk_products_category_id_categories"),
        "products",
        "categories",
        ["category_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("event_type", sa.String(length=160), nullable=False),
        sa.Column("aggregate_type", sa.String(length=80), nullable=False),
        sa.Column("aggregate_id", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("occurred_at", UTCDateTime(), nullable=False),
        sa.Column("published_at", UTCDateTime(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
    )
    op.create_index(op.f("ix_outbox_events_aggregate_id"), "outbox_events", ["aggregate_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_outbox_events_aggregate_id"), table_name="outbox_events")
    op.drop_table("outbox_events")
    inspector = sa.inspect(op.get_bind())
    product_foreign_keys = {
        foreign_key["name"] for foreign_key in inspector.get_foreign_keys("products")
    }
    product_indexes = {index["name"] for index in inspector.get_indexes("products")}
    product_columns = {column["name"] for column in inspector.get_columns("products")}
    if op.f("fk_products_category_id_categories") in product_foreign_keys:
        op.drop_constraint(
            op.f("fk_products_category_id_categories"),
            "products",
            type_="foreignkey",
        )
    if op.f("ix_products_category_id") in product_indexes:
        op.drop_index(op.f("ix_products_category_id"), table_name="products")
    if "category_id" in product_columns:
        op.drop_column("products", "category_id")

    categories_foreign_keys = {
        foreign_key["name"] for foreign_key in inspector.get_foreign_keys("categories")
    }
    categories_indexes = {index["name"] for index in inspector.get_indexes("categories")}
    if op.f("fk_categories_parent_id_categories") in categories_foreign_keys:
        op.drop_constraint(
            op.f("fk_categories_parent_id_categories"),
            "categories",
            type_="foreignkey",
        )
    if op.f("ix_categories_parent_id") in categories_indexes:
        op.drop_index(op.f("ix_categories_parent_id"), table_name="categories")
    op.drop_table("categories")
