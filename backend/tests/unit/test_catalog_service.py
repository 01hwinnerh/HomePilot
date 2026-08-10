import asyncio

import pytest
from pydantic import ValidationError

from app.modules.catalog.models import SKU, Product, ProductStatus, Store
from app.modules.catalog.schemas import SKUCreate
from app.modules.catalog.service import (
    CatalogConflict,
    CatalogService,
    InvalidCatalogState,
)
from app.modules.merchants.models import Merchant, MerchantMember, MerchantMemberRole
from app.shared.tenancy.context import TenantContext, TenantContextFactory, _issue_principal


class RecordingSession:
    def __init__(self, scalar_values: list[object | None] | None = None) -> None:
        self.scalar_values = list(scalar_values or [])
        self.added: list[object] = []
        self.committed = False
        self.rolled_back = False

    async def scalar(self, statement: object) -> object | None:
        return self.scalar_values.pop(0) if self.scalar_values else None

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        for index, instance in enumerate(self.added, start=1):
            if getattr(instance, "id", None) is None:
                instance.id = index

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


def trusted_context() -> TenantContext:
    member = MerchantMember(
        user_id=7,
        merchant_id=1,
        role=MerchantMemberRole.OWNER,
        is_active=True,
    )
    merchant = Merchant(id=1, name="Merchant A", is_active=True)

    class ContextSession:
        def __init__(self) -> None:
            self.results = [member, merchant]

        async def scalar(self, statement: object) -> object:
            return self.results.pop(0)

    return asyncio.run(
        TenantContextFactory(session=ContextSession()).for_merchant(
            principal=_issue_principal(user_id=7, is_platform_admin=False),
            merchant_id=1,
        )
    )


def test_sku_schema_rejects_negative_price() -> None:
    with pytest.raises(ValidationError):
        SKUCreate(
            product_id=1,
            sku_code="TABLE-WALNUT",
            sku_name="Walnut",
            variant_attributes={"color": "Walnut"},
            price_minor=-1,
        )


def test_new_product_starts_as_draft() -> None:
    store = Store(id=7, merchant_id=1, name="Demo Store", slug="demo-store")
    session = RecordingSession([store])

    product = asyncio.run(
        CatalogService(session=session, context=trusted_context()).create_product(
            store_id=7,
            name="Dining Table",
            description="Solid wood table",
        )
    )

    assert product.status is ProductStatus.DRAFT
    assert product.merchant_id == 1
    assert product.store_id == 7
    assert session.committed is True


def test_create_sku_rejects_duplicate_code_within_merchant() -> None:
    product = Product(
        id=9,
        merchant_id=1,
        store_id=7,
        name="Dining Table",
        description="Solid wood table",
        status=ProductStatus.DRAFT,
    )
    duplicate = SKU(
        id=10,
        merchant_id=1,
        product_id=8,
        sku_code="TABLE-WALNUT",
        sku_name="Existing Walnut",
        variant_attributes={"color": "Walnut"},
        price_minor=19900,
        currency="CNY",
        is_active=True,
    )
    session = RecordingSession([product, duplicate])

    with pytest.raises(CatalogConflict):
        asyncio.run(
            CatalogService(session=session, context=trusted_context()).create_sku(
                product_id=9,
                sku_code="TABLE-WALNUT",
                sku_name="New Walnut",
                variant_attributes={"color": "Walnut"},
                price_minor=19900,
                currency="CNY",
            )
        )

    assert session.rolled_back is True


def test_publish_requires_an_active_sku() -> None:
    product = Product(
        id=9,
        merchant_id=1,
        store_id=7,
        name="Dining Table",
        description="Solid wood table",
        status=ProductStatus.DRAFT,
    )
    store = Store(id=7, merchant_id=1, name="Demo Store", slug="demo-store")
    session = RecordingSession([product, store, None])

    with pytest.raises(InvalidCatalogState):
        asyncio.run(
            CatalogService(session=session, context=trusted_context()).publish_product(
                product_id=9
            )
        )

    assert session.rolled_back is True


def test_publish_with_an_active_sku_commits_published_state() -> None:
    product = Product(
        id=9,
        merchant_id=1,
        store_id=7,
        name="Dining Table",
        description="Solid wood table",
        status=ProductStatus.DRAFT,
    )
    active_sku = SKU(
        id=10,
        merchant_id=1,
        product_id=9,
        sku_code="TABLE-WALNUT",
        sku_name="Walnut",
        variant_attributes={"color": "Walnut"},
        price_minor=19900,
        currency="CNY",
        is_active=True,
    )
    store = Store(id=7, merchant_id=1, name="Demo Store", slug="demo-store")
    session = RecordingSession([product, store, active_sku])

    result = asyncio.run(
        CatalogService(session=session, context=trusted_context()).publish_product(
            product_id=9
        )
    )

    assert result.status is ProductStatus.PUBLISHED
    assert session.committed is True


def test_archived_product_cannot_be_republished() -> None:
    product = Product(
        id=9,
        merchant_id=1,
        store_id=7,
        name="Dining Table",
        description="Solid wood table",
        status=ProductStatus.ARCHIVED,
    )
    session = RecordingSession([product])

    with pytest.raises(InvalidCatalogState):
        asyncio.run(
            CatalogService(session=session, context=trusted_context()).publish_product(
                product_id=9
            )
        )

    assert session.rolled_back is True
