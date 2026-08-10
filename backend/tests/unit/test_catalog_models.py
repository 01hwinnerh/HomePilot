from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Table, UniqueConstraint

from app.modules.catalog.models import SKU, Category, Product, ProductStatus, Store
from app.shared.models.tenant import MerchantOwnedMixin
from app.shared.models.timestamps import TimestampMixin


def unique_constraint_columns(table: Table) -> set[frozenset[str]]:
    return {
        frozenset(column.name for column in constraint.columns)
        for constraint in table.constraints
        if isinstance(constraint, UniqueConstraint)
    }


def test_catalog_models_share_tenant_and_timestamp_boundaries() -> None:
    assert all(issubclass(model, MerchantOwnedMixin) for model in (Store, Product, SKU))
    assert all(issubclass(model, TimestampMixin) for model in (Store, Product, SKU))


def test_catalog_relationships_keep_product_store_and_sku_product_chain() -> None:
    assert "store_id" in Product.__table__.c
    assert "product_id" in SKU.__table__.c
    assert "store_id" not in SKU.__table__.c
    assert any(
        isinstance(constraint, ForeignKeyConstraint)
        and {column.name for column in constraint.columns} == {"merchant_id", "store_id"}
        for constraint in Product.__table__.constraints
    )
    assert any(
        isinstance(constraint, ForeignKeyConstraint)
        and {column.name for column in constraint.columns} == {"merchant_id", "product_id"}
        for constraint in SKU.__table__.constraints
    )


def test_catalog_uniqueness_and_price_constraints_are_explicit() -> None:
    assert frozenset({"merchant_id", "slug"}) in unique_constraint_columns(Store.__table__)
    assert frozenset({"merchant_id", "sku_code"}) in unique_constraint_columns(SKU.__table__)
    assert any(
        isinstance(constraint, CheckConstraint)
        and constraint.name == "ck_skus_price_minor_non_negative"
        for constraint in SKU.__table__.constraints
    )


def test_product_statuses_are_limited_to_draft_published_and_archived() -> None:
    assert {status.value for status in ProductStatus} == {
        "DRAFT",
        "PUBLISHED",
        "ARCHIVED",
    }


def test_category_tree_and_product_category_foreign_key_are_explicit() -> None:
    assert {"id", "parent_id", "slug", "name", "sort_order", "is_active"} <= {
        column.name for column in Category.__table__.c
    }
    assert frozenset({"slug"}) in unique_constraint_columns(Category.__table__)
    assert "category_id" in Product.__table__.c
    assert any(
        isinstance(constraint, ForeignKeyConstraint)
        and {column.name for column in constraint.columns} == {"category_id"}
        for constraint in Product.__table__.constraints
    )
