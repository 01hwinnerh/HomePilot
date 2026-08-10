from enum import StrEnum

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Enum,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base
from app.shared.models.tenant import MerchantOwnedMixin
from app.shared.models.timestamps import TimestampMixin


class ProductStatus(StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    ARCHIVED = "ARCHIVED"


class Store(MerchantOwnedMixin, TimestampMixin, Base):
    """A merchant-owned storefront; one merchant may own multiple stores."""

    __tablename__ = "stores"

    __table_args__ = (
        UniqueConstraint("merchant_id", "slug", name="uq_stores_merchant_slug"),
        UniqueConstraint("merchant_id", "id", name="uq_stores_merchant_id_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    slug: Mapped[str] = mapped_column(String(160), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Product(MerchantOwnedMixin, TimestampMixin, Base):
    """A merchant-owned product listed by one store."""

    __tablename__ = "products"

    __table_args__ = (
        ForeignKeyConstraint(
            ["merchant_id", "store_id"],
            ["stores.merchant_id", "stores.id"],
            name="fk_products_merchant_store",
        ),
        UniqueConstraint("merchant_id", "id", name="uq_products_merchant_id_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(4000), nullable=False, default="")
    status: Mapped[ProductStatus] = mapped_column(
        Enum(
            ProductStatus,
            name="product_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
        default=ProductStatus.DRAFT,
    )


class SKU(MerchantOwnedMixin, TimestampMixin, Base):
    """A sellable product variant; store ownership comes through Product."""

    __tablename__ = "skus"

    __table_args__ = (
        ForeignKeyConstraint(
            ["merchant_id", "product_id"],
            ["products.merchant_id", "products.id"],
            name="fk_skus_merchant_product",
        ),
        UniqueConstraint("merchant_id", "sku_code", name="uq_skus_merchant_code"),
        CheckConstraint("price_minor >= 0", name="price_minor_non_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    sku_code: Mapped[str] = mapped_column(String(120), nullable=False)
    sku_name: Mapped[str] = mapped_column(String(200), nullable=False)
    variant_attributes: Mapped[dict[str, object]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )
    price_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CNY")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
