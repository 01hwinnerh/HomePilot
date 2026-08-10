"""Local-only catalog data for the two HomePilot demo merchants."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import SKU, Product, ProductStatus, Store
from app.modules.merchants.models import Merchant


class CatalogSeedConflictError(ValueError):
    """Raised when existing catalog data is unsafe to treat as demo data."""


DEMO_CATALOG = (
    {
        "merchant_name": "HomePilot Demo Merchant A",
        "store_name": "HomePilot Demo Merchant A Store",
        "store_slug": "demo-merchant-a",
        "product_name": "Walnut Dining Table",
        "product_description": "A solid walnut table for the dining room.",
        "sku_code": "DEMO-A-TABLE-WALNUT",
        "sku_name": "Walnut 1.8m",
        "variant_attributes": {"color": "Walnut", "size": "1.8m"},
        "price_minor": 19900,
    },
    {
        "merchant_name": "HomePilot Demo Merchant B",
        "store_name": "HomePilot Demo Merchant B Store",
        "store_slug": "demo-merchant-b",
        "product_name": "Linen Lounge Chair",
        "product_description": "A linen lounge chair for a quiet reading corner.",
        "sku_code": "DEMO-B-CHAIR-LINEN",
        "sku_name": "Natural linen",
        "variant_attributes": {"color": "Natural", "material": "Linen"},
        "price_minor": 12900,
    },
)


async def seed_catalog_demo_data(session: AsyncSession) -> None:
    """Create or verify one published demo product for each demo merchant."""

    try:
        for demo in DEMO_CATALOG:
            merchant = await session.scalar(
                select(Merchant).where(Merchant.name == demo["merchant_name"])
            )
            if merchant is None or not merchant.is_active:
                raise CatalogSeedConflictError(
                    f"Expected active demo merchant is missing: {demo['merchant_name']}"
                )

            store = await _get_or_create_store(session, merchant.id, demo)
            product = await _get_or_create_product(session, merchant.id, store.id, demo)
            await _get_or_create_sku(session, merchant.id, product.id, demo)

        await session.flush()
    except CatalogSeedConflictError:
        await session.rollback()
        raise


async def _get_or_create_store(
    session: AsyncSession,
    merchant_id: int,
    demo: dict[str, object],
) -> Store:
    store = await session.scalar(
        select(Store).where(
            Store.merchant_id == merchant_id,
            Store.slug == demo["store_slug"],
        )
    )
    if store is not None:
        if not store.is_active or store.name != demo["store_name"]:
            raise CatalogSeedConflictError(
                f"Existing demo store does not match: {demo['store_slug']}"
            )
        return store

    store = Store(
        merchant_id=merchant_id,
        name=str(demo["store_name"]),
        slug=str(demo["store_slug"]),
        is_active=True,
    )
    session.add(store)
    await session.flush()
    return store


async def _get_or_create_product(
    session: AsyncSession,
    merchant_id: int,
    store_id: int,
    demo: dict[str, object],
) -> Product:
    product = await session.scalar(
        select(Product).where(
            Product.merchant_id == merchant_id,
            Product.store_id == store_id,
            Product.name == demo["product_name"],
        )
    )
    if product is not None:
        if (
            product.status != ProductStatus.PUBLISHED
            or product.description != demo["product_description"]
        ):
            raise CatalogSeedConflictError(
                f"Existing demo product does not match: {demo['product_name']}"
            )
        return product

    product = Product(
        merchant_id=merchant_id,
        store_id=store_id,
        name=str(demo["product_name"]),
        description=str(demo["product_description"]),
        status=ProductStatus.PUBLISHED,
    )
    session.add(product)
    await session.flush()
    return product


async def _get_or_create_sku(
    session: AsyncSession,
    merchant_id: int,
    product_id: int,
    demo: dict[str, object],
) -> SKU:
    sku = await session.scalar(
        select(SKU).where(
            SKU.merchant_id == merchant_id,
            SKU.sku_code == demo["sku_code"],
        )
    )
    expected_attributes = demo["variant_attributes"]
    if sku is not None:
        if (
            sku.product_id != product_id
            or not sku.is_active
            or sku.sku_name != demo["sku_name"]
            or sku.variant_attributes != expected_attributes
            or sku.price_minor != demo["price_minor"]
            or sku.currency != "CNY"
        ):
            raise CatalogSeedConflictError(
                f"Existing demo SKU does not match: {demo['sku_code']}"
            )
        return sku

    sku = SKU(
        merchant_id=merchant_id,
        product_id=product_id,
        sku_code=str(demo["sku_code"]),
        sku_name=str(demo["sku_name"]),
        variant_attributes=expected_attributes,  # type: ignore[arg-type]
        price_minor=int(demo["price_minor"]),
        currency="CNY",
        is_active=True,
    )
    session.add(sku)
    return sku
