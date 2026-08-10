import asyncio
from collections.abc import AsyncIterator

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.v1.catalog import get_catalog_search
from app.api.v1.dependencies import get_db_session
from app.core.database import get_db_session as production_get_db_session
from app.main import app
from app.modules.catalog.models import SKU, Product, ProductStatus, Store
from app.modules.catalog.search.contracts import SearchHit
from app.modules.merchants.models import Merchant


def test_search_rechecks_mysql_visibility_and_returns_categories(
    migrated_identity_database_url: str,
) -> None:
    asyncio.run(_search_rechecks_mysql_visibility(migrated_identity_database_url))


def test_search_unavailable_returns_safe_503(
    migrated_identity_database_url: str,
) -> None:
    asyncio.run(_search_unavailable_returns_safe_503(migrated_identity_database_url))


def _session_override(session_factory: async_sessionmaker[AsyncSession]):
    async def override() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    return override


async def _add_public_product(
    session: AsyncSession,
    *,
    merchant_name: str,
    product_name: str,
    status: ProductStatus,
) -> Product:
    merchant = Merchant(name=merchant_name, is_active=True)
    session.add(merchant)
    await session.flush()
    store = Store(
        merchant_id=merchant.id,
        name=f"{merchant_name} Store",
        slug=merchant_name.lower(),
    )
    session.add(store)
    await session.flush()
    product = Product(
        merchant_id=merchant.id,
        store_id=store.id,
        category_id=1,
        name=product_name,
        description="Searchable home furniture",
        status=status,
    )
    session.add(product)
    await session.flush()
    session.add(
        SKU(
            merchant_id=merchant.id,
            product_id=product.id,
            sku_code=f"{merchant_name.upper()}-SKU",
            sku_name="Default",
            variant_attributes={},
            price_minor=19900,
            currency="CNY",
            is_active=True,
        )
    )
    await session.commit()
    return product


async def _search_rechecks_mysql_visibility(database_url: str) -> None:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            visible = await _add_public_product(
                session,
                merchant_name="Visible Merchant",
                product_name="Visible Sofa",
                status=ProductStatus.PUBLISHED,
            )
            stale = await _add_public_product(
                session,
                merchant_name="Stale Merchant",
                product_name="Stale Sofa",
                status=ProductStatus.ARCHIVED,
            )

        class FakeSearch:
            async def search_product_ids(self, **kwargs: object) -> list[SearchHit]:
                return [
                    SearchHit(product_id=stale.id, score=2),
                    SearchHit(product_id=visible.id, score=1),
                ]

        async def override_search() -> FakeSearch:
            return FakeSearch()

        override_session = _session_override(session_factory)
        app.dependency_overrides[production_get_db_session] = override_session
        app.dependency_overrides[get_db_session] = override_session
        app.dependency_overrides[get_catalog_search] = override_search
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/catalog/products", params={"q": "sofa"})
            categories = await client.get("/api/v1/catalog/categories")

        assert response.status_code == 200
        assert [item["id"] for item in response.json()] == [visible.id]
        assert response.json()[0]["merchant_name"] == "Visible Merchant"
        assert categories.status_code == 200
        assert any(category["id"] == 1 for category in categories.json())
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def _search_unavailable_returns_safe_503(database_url: str) -> None:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        class BrokenSearch:
            async def search_product_ids(self, **kwargs: object) -> list[SearchHit]:
                raise TimeoutError("Elasticsearch is down")

        async def override_search() -> BrokenSearch:
            return BrokenSearch()

        override_session = _session_override(session_factory)
        app.dependency_overrides[production_get_db_session] = override_session
        app.dependency_overrides[get_db_session] = override_session
        app.dependency_overrides[get_catalog_search] = override_search
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.get("/api/v1/catalog/products", params={"q": "sofa"})

        assert response.status_code == 503
        assert response.json() == {"detail": "SEARCH_UNAVAILABLE"}
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
