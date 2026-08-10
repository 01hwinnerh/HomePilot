"""Create merchant catalog foundation tables.

Revision ID: 20260809_0003
Revises: 20260805_0002
Create Date: 2026-08-09
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20260809_0003"
down_revision: str | None = "20260805_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "stores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("merchant_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("slug", sa.String(length=160), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["merchant_id"],
            ["merchants.id"],
            name=op.f("fk_stores_merchant_id_merchants"),
        ),
        sa.UniqueConstraint("merchant_id", "slug", name=op.f("uq_stores_merchant_slug")),
        sa.UniqueConstraint(
            "merchant_id",
            "id",
            name=op.f("uq_stores_merchant_id_id"),
        ),
    )
    op.create_index(op.f("ix_stores_merchant_id"), "stores", ["merchant_id"], unique=False)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("merchant_id", sa.Integer(), nullable=False),
        sa.Column("store_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=4000), nullable=False, server_default=""),
        sa.Column(
            "status",
            sa.Enum(
                "DRAFT",
                "PUBLISHED",
                "ARCHIVED",
                name="product_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
            server_default="DRAFT",
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["merchant_id"],
            ["merchants.id"],
            name=op.f("fk_products_merchant_id_merchants"),
        ),
        sa.ForeignKeyConstraint(
            ["merchant_id", "store_id"],
            ["stores.merchant_id", "stores.id"],
            name=op.f("fk_products_merchant_store"),
        ),
        sa.UniqueConstraint(
            "merchant_id",
            "id",
            name=op.f("uq_products_merchant_id_id"),
        ),
    )
    op.create_index(op.f("ix_products_merchant_id"), "products", ["merchant_id"], unique=False)
    op.create_index(op.f("ix_products_store_id"), "products", ["store_id"], unique=False)

    op.create_table(
        "skus",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("merchant_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("sku_code", sa.String(length=120), nullable=False),
        sa.Column("sku_name", sa.String(length=200), nullable=False),
        sa.Column("variant_attributes", sa.JSON(), nullable=False),
        sa.Column("price_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="CNY"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["merchant_id"],
            ["merchants.id"],
            name=op.f("fk_skus_merchant_id_merchants"),
        ),
        sa.ForeignKeyConstraint(
            ["merchant_id", "product_id"],
            ["products.merchant_id", "products.id"],
            name=op.f("fk_skus_merchant_product"),
        ),
        sa.UniqueConstraint(
            "merchant_id",
            "sku_code",
            name=op.f("uq_skus_merchant_code"),
        ),
        sa.CheckConstraint("price_minor >= 0", name="price_minor_non_negative"),
    )
    op.create_index(op.f("ix_skus_merchant_id"), "skus", ["merchant_id"], unique=False)
    op.create_index(op.f("ix_skus_product_id"), "skus", ["product_id"], unique=False)


def downgrade() -> None:
    op.drop_table("skus")
    op.drop_table("products")
    op.drop_table("stores")
