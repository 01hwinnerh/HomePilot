import asyncio
from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.v1.auth import get_auth_rate_limiter
from app.api.v1.dependencies import get_db_session
from app.core.database import get_db_session as production_get_db_session
from app.core.security import hash_password
from app.main import app
from app.modules.catalog.models import SKU, Product, ProductStatus, Store
from app.modules.merchants.models import Merchant, MerchantMember, MerchantMemberRole
from app.shared.outbox.models import OutboxEvent


class NoOpRateLimiter:
    async def check_request(self, *, client_ip: str) -> None:
        return None

    async def check_credentials(self, *, identity: str, client_ip: str) -> None:
        return None

    async def check(self, *, scope: str, identity: str, client_ip: str) -> None:
        return None

    async def record_credential_failure(self, *, identity: str, client_ip: str) -> None:
        return None

    async def clear_credential_failures(self, *, identity: str, client_ip: str) -> None:
        return None


def test_member_can_create_a_store_within_their_merchant(
    migrated_identity_database_url: str,
) -> None:
    asyncio.run(_member_can_create_store(migrated_identity_database_url))


def test_public_catalog_only_returns_published_products_from_active_storefronts(
    migrated_identity_database_url: str,
) -> None:
    asyncio.run(_public_catalog_filters_hidden_products(migrated_identity_database_url))


def test_catalog_outbox_event_rolls_back_with_business_transaction(
    migrated_identity_database_url: str,
) -> None:
    asyncio.run(_catalog_outbox_rolls_back(migrated_identity_database_url))


async def _catalog_outbox_rolls_back(database_url: str) -> None:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            with pytest.raises(RuntimeError):
                async with session.begin():
                    session.add(
                        OutboxEvent(
                            event_type="catalog.product.changed",
                            aggregate_type="product",
                            aggregate_id=99,
                            payload={},
                        )
                    )
                    raise RuntimeError("force transaction rollback")

            assert await session.scalar(select(func.count()).select_from(OutboxEvent)) == 0
    finally:
        await engine.dispose()


async def _member_can_create_store(database_url: str) -> None:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[production_get_db_session] = override_get_db_session
    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_auth_rate_limiter] = NoOpRateLimiter
    try:
        async with session_factory() as session:
            merchant = Merchant(name="Merchant A", is_active=True)
            session.add(merchant)
            await session.flush()
            user_id = 1
            from app.modules.identity.models import User

            session.add(
                User(
                    id=user_id,
                    email="catalog-owner@example.com",
                    password_hash=hash_password("safe-password-123"),
                    is_active=True,
                    is_platform_admin=False,
                )
            )
            await session.flush()
            session.add(
                MerchantMember(
                    user_id=user_id,
                    merchant_id=merchant.id,
                    role=MerchantMemberRole.OWNER,
                    is_active=True,
                )
            )
            await session.commit()

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            login = await client.post(
                "/api/v1/auth/login",
                json={"email": "catalog-owner@example.com", "password": "safe-password-123"},
            )
            assert login.status_code == 200
            token = login.json()["access_token"]
            response = await client.post(
                f"/api/v1/merchants/{merchant.id}/stores",
                headers={"Authorization": f"Bearer {token}"},
                json={"name": "Merchant A Store", "slug": "merchant-a-store"},
            )

            assert response.status_code == 201
            assert response.json()["merchant_id"] == merchant.id

            store_id = response.json()["id"]
            product_response = await client.post(
                f"/api/v1/merchants/{merchant.id}/stores/{store_id}/products",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "store_id": store_id,
                    "category_id": 1,
                    "name": "Dining Table",
                    "description": "Solid wood table",
                },
            )
            assert product_response.status_code == 201
            product_id = product_response.json()["id"]
            assert product_response.json()["status"] == "DRAFT"

            sku_response = await client.post(
                f"/api/v1/merchants/{merchant.id}/products/{product_id}/skus",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "product_id": product_id,
                    "sku_code": "TABLE-WALNUT",
                    "sku_name": "Walnut 1.8m",
                    "variant_attributes": {"color": "Walnut", "size": "1.8m"},
                    "price_minor": 19900,
                    "currency": "CNY",
                },
            )
            assert sku_response.status_code == 201

            published = await client.post(
                f"/api/v1/merchants/{merchant.id}/products/{product_id}/publish",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert published.status_code == 200
            assert published.json()["status"] == "PUBLISHED"

            stores = await client.get(
                f"/api/v1/merchants/{merchant.id}/stores",
                headers={"Authorization": f"Bearer {token}"},
            )
            products = await client.get(
                f"/api/v1/merchants/{merchant.id}/products",
                params={"status": "PUBLISHED", "category_id": 1},
                headers={"Authorization": f"Bearer {token}"},
            )
            skus = await client.get(
                f"/api/v1/merchants/{merchant.id}/products/{product_id}/skus",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert [store["id"] for store in stores.json()] == [store_id]
            assert [product["id"] for product in products.json()] == [product_id]
            assert [sku["sku_code"] for sku in skus.json()] == ["TABLE-WALNUT"]

            async with session_factory() as session:
                merchant_b = Merchant(name="Merchant B", is_active=True)
                session.add(merchant_b)
                await session.flush()
                store_b = Store(
                    merchant_id=merchant_b.id,
                    name="Merchant B Store",
                    slug="merchant-b-store",
                )
                session.add(store_b)
                await session.flush()
                product_b = Product(
                    merchant_id=merchant_b.id,
                    store_id=store_b.id,
                    category_id=1,
                    name="Merchant B Product",
                    description="B only",
                    status=ProductStatus.DRAFT,
                )
                session.add(product_b)
                await session.commit()
                product_b_id = product_b.id

            cross_tenant = await client.get(
                f"/api/v1/merchants/{merchant.id}/products/{product_b_id}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert cross_tenant.status_code == 404

            unauthenticated = await client.get(
                f"/api/v1/merchants/{merchant.id}/products/{product_id}"
            )
            assert unauthenticated.status_code == 401
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def _public_catalog_filters_hidden_products(database_url: str) -> None:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[production_get_db_session] = override_get_db_session
    try:
        async with session_factory() as session:
            merchant = Merchant(name="Public Merchant", is_active=True)
            hidden_merchant = Merchant(name="Hidden Merchant", is_active=False)
            session.add_all([merchant, hidden_merchant])
            await session.flush()
            store = Store(merchant_id=merchant.id, name="Public Store", slug="public-store")
            hidden_store = Store(
                merchant_id=hidden_merchant.id,
                name="Hidden Store",
                slug="hidden-store",
            )
            session.add_all([store, hidden_store])
            await session.flush()
            published = Product(
                merchant_id=merchant.id,
                store_id=store.id,
                category_id=1,
                name="Published Table",
                description="Visible",
                status=ProductStatus.PUBLISHED,
            )
            draft = Product(
                merchant_id=merchant.id,
                store_id=store.id,
                category_id=1,
                name="Draft Table",
                description="Hidden",
                status=ProductStatus.DRAFT,
            )
            hidden = Product(
                merchant_id=hidden_merchant.id,
                store_id=hidden_store.id,
                category_id=1,
                name="Hidden Merchant Table",
                description="Hidden",
                status=ProductStatus.PUBLISHED,
            )
            session.add_all([published, draft, hidden])
            await session.flush()
            session.add_all(
                [
                    SKU(
                        merchant_id=merchant.id,
                        product_id=published.id,
                        sku_code="PUBLIC-TABLE",
                        sku_name="Public",
                        variant_attributes={"color": "Oak"},
                        price_minor=19900,
                        currency="CNY",
                        is_active=True,
                    ),
                    SKU(
                        merchant_id=merchant.id,
                        product_id=published.id,
                        sku_code="PUBLIC-TABLE-INACTIVE",
                        sku_name="Inactive",
                        variant_attributes={"color": "Black"},
                        price_minor=20900,
                        currency="CNY",
                        is_active=False,
                    ),
                ]
            )
            await session.commit()
            published_id = published.id
            hidden_id = hidden.id

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            listing = await client.get("/api/v1/catalog/products")
            assert listing.status_code == 200
            assert [product["id"] for product in listing.json()] == [published_id]

            detail = await client.get(f"/api/v1/catalog/products/{published_id}")
            assert detail.status_code == 200
            assert detail.json()["name"] == "Published Table"
            assert [sku["sku_code"] for sku in detail.json()["skus"]] == ["PUBLIC-TABLE"]

            hidden_detail = await client.get(f"/api/v1/catalog/products/{hidden_id}")
            assert hidden_detail.status_code == 404
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
