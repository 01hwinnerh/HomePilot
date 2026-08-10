import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import command

BACKEND_ROOT = Path(__file__).resolve().parents[2]
CATALOG_TABLES = {"stores", "products", "skus"}


@pytest.fixture
def migrated_catalog_database_url(
    isolated_test_database_url: str,
) -> Iterator[str]:
    alembic_config = Config(BACKEND_ROOT / "alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", isolated_test_database_url)

    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")
    try:
        yield isolated_test_database_url
    finally:
        command.downgrade(alembic_config, "base")
        assert asyncio.run(read_catalog_tables(isolated_test_database_url)) == set()


def test_catalog_migration_creates_all_tables_and_relationship_columns(
    migrated_catalog_database_url: str,
) -> None:
    assert asyncio.run(read_catalog_tables(migrated_catalog_database_url)) == CATALOG_TABLES
    assert asyncio.run(read_columns(migrated_catalog_database_url, "stores")) >= {
        "id",
        "merchant_id",
        "name",
        "slug",
        "is_active",
        "created_at",
        "updated_at",
    }
    assert asyncio.run(read_columns(migrated_catalog_database_url, "products")) >= {
        "id",
        "merchant_id",
        "store_id",
        "name",
        "description",
        "status",
        "created_at",
        "updated_at",
    }
    assert asyncio.run(read_columns(migrated_catalog_database_url, "skus")) >= {
        "id",
        "merchant_id",
        "product_id",
        "sku_code",
        "sku_name",
        "variant_attributes",
        "price_minor",
        "currency",
        "is_active",
        "created_at",
        "updated_at",
    }


def test_catalog_migration_has_scoped_unique_indexes(
    migrated_catalog_database_url: str,
) -> None:
    assert asyncio.run(
        read_unique_indexes(migrated_catalog_database_url, "stores")
    ) >= {("merchant_id", "slug")}
    assert asyncio.run(
        read_unique_indexes(migrated_catalog_database_url, "skus")
    ) >= {("merchant_id", "sku_code")}


async def read_catalog_tables(database_url: str) -> set[str]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() AND table_name IN "
                    "('stores', 'products', 'skus')"
                )
            )
            return set(result.scalars().all())
    finally:
        await engine.dispose()


async def read_columns(database_url: str, table_name: str) -> set[str]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_schema = DATABASE() AND table_name = :table_name"
                ),
                {"table_name": table_name},
            )
            return set(result.scalars().all())
    finally:
        await engine.dispose()


async def read_unique_indexes(database_url: str, table_name: str) -> set[tuple[str, ...]]:
    engine = create_async_engine(database_url)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT index_name, column_name FROM information_schema.statistics "
                    "WHERE table_schema = DATABASE() AND table_name = :table_name "
                    "AND non_unique = 0 ORDER BY index_name, seq_in_index"
                ),
                {"table_name": table_name},
            )
            indexes: dict[str, list[str]] = {}
            for index_name, column_name in result:
                indexes.setdefault(index_name, []).append(column_name)
            return {tuple(columns) for columns in indexes.values() if len(columns) > 1}
    finally:
        await engine.dispose()
