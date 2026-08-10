import asyncio

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.modules.catalog.demo_seed import (
    CatalogSeedConflictError,
    seed_catalog_demo_data,
)
from app.modules.catalog.models import SKU, Category, Product, Store
from app.modules.merchants.models import Merchant


def test_catalog_seed_creates_two_merchants_catalogs_and_is_idempotent(
    migrated_identity_database_url: str,
) -> None:
    asyncio.run(_seed_catalog_twice(migrated_identity_database_url))


async def _seed_catalog_twice(database_url: str) -> None:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            session.add_all(
                [
                    Merchant(name="HomePilot Demo Merchant A", is_active=True),
                    Merchant(name="HomePilot Demo Merchant B", is_active=True),
                ]
            )
            await session.commit()

            await seed_catalog_demo_data(session)
            await session.commit()
            await seed_catalog_demo_data(session)
            await session.commit()

            assert await session.scalar(select(func.count()).select_from(Store)) == 2
            assert await session.scalar(select(func.count()).select_from(Category)) == 5
            assert await session.scalar(select(func.count()).select_from(Product)) == 2
            assert await session.scalar(select(func.count()).select_from(SKU)) == 2
    finally:
        await engine.dispose()


def test_catalog_seed_conflict_rolls_back_without_overwriting(
    migrated_identity_database_url: str,
) -> None:
    asyncio.run(_seed_catalog_conflict(migrated_identity_database_url))


async def _seed_catalog_conflict(database_url: str) -> None:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            session.add(Merchant(name="HomePilot Demo Merchant A", is_active=False))
            await session.commit()

            with pytest.raises(CatalogSeedConflictError):
                await seed_catalog_demo_data(session)

            assert session.in_transaction() is False
            assert await session.scalar(select(func.count()).select_from(Store)) == 0
    finally:
        await engine.dispose()
