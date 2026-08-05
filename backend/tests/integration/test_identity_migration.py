import asyncio
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from alembic.config import Config
from sqlalchemy import select, text
from sqlalchemy.exc import DatabaseError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from alembic import command
from app.modules.identity.models import AuthSession, User

BACKEND_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def migrated_identity_database_url(
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
        assert asyncio.run(read_identity_tables(isolated_test_database_url)) == set()


def test_identity_migration_creates_users_with_unique_email(
    migrated_identity_database_url: str,
) -> None:
    columns = asyncio.run(read_table_columns(migrated_identity_database_url, "users"))
    _, unique_indexes = asyncio.run(
        read_table_indexes(migrated_identity_database_url, "users")
    )

    assert {
        "id",
        "email",
        "password_hash",
        "is_active",
        "is_platform_admin",
        "created_at",
        "updated_at",
    } <= columns
    assert ("email",) in unique_indexes


async def read_table_columns(database_url: str, table_name: str) -> set[str]:
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


async def read_identity_tables(database_url: str) -> set[str]:
    engine = create_async_engine(database_url)

    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() AND table_name IN "
                    "('users', 'merchants', 'merchant_members', 'auth_sessions')"
                )
            )
            return set(result.scalars().all())
    finally:
        await engine.dispose()


async def read_table_indexes(
    database_url: str,
    table_name: str,
) -> tuple[set[tuple[str, ...]], set[tuple[str, ...]]]:
    engine = create_async_engine(database_url)

    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT index_name, column_name, non_unique "
                    "FROM information_schema.statistics "
                    "WHERE table_schema = DATABASE() AND table_name = :table_name "
                    "ORDER BY index_name, seq_in_index"
                ),
                {"table_name": table_name},
            )
            indexes: dict[str, list[str]] = {}
            unique_index_names: set[str] = set()
            for index_name, column_name, non_unique in result:
                indexes.setdefault(index_name, []).append(column_name)
                if non_unique == 0:
                    unique_index_names.add(index_name)

            all_indexes = {tuple(columns) for columns in indexes.values()}
            unique_indexes = {
                tuple(indexes[index_name]) for index_name in unique_index_names
            }
            return all_indexes, unique_indexes
    finally:
        await engine.dispose()


async def read_table_foreign_keys(
    database_url: str,
    table_name: str,
) -> set[tuple[str, str, str]]:
    engine = create_async_engine(database_url)

    try:
        async with engine.connect() as connection:
            result = await connection.execute(
                text(
                    "SELECT column_name, referenced_table_name, referenced_column_name "
                    "FROM information_schema.key_column_usage "
                    "WHERE table_schema = DATABASE() AND table_name = :table_name "
                    "AND referenced_table_name IS NOT NULL"
                ),
                {"table_name": table_name},
            )
            return {tuple(row) for row in result}
    finally:
        await engine.dispose()


async def persist_and_read_session_expiry(database_url: str) -> datetime:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    expires_at = datetime(2026, 8, 5, 20, tzinfo=timezone(timedelta(hours=8)))

    try:
        async with session_factory() as session:
            user = User(
                email="utc.roundtrip@homepilot.test",
                password_hash="not-a-secret",
            )
            session.add(user)
            await session.flush()

            auth_session = AuthSession(
                user_id=user.id,
                refresh_token_hash="a" * 64,
                expires_at=expires_at,
            )
            session.add(auth_session)
            await session.commit()
            auth_session_id = auth_session.id

        async with session_factory() as session:
            result = await session.scalar(
                select(AuthSession.expires_at).where(AuthSession.id == auth_session_id)
            )
            assert result is not None
            return result
    finally:
        await engine.dispose()


async def insert_invalid_merchant_member_role(database_url: str) -> None:
    engine = create_async_engine(database_url)
    created_at = datetime(2026, 8, 5, 12)

    try:
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "INSERT INTO users "
                    "(id, email, password_hash, is_active, is_platform_admin, "
                    "created_at, updated_at) "
                    "VALUES (1, 'role.check@homepilot.test', 'not-a-secret', "
                    "true, false, :created_at, :created_at)"
                ),
                {"created_at": created_at},
            )
            await connection.execute(
                text(
                    "INSERT INTO merchants (id, name, is_active, created_at, updated_at) "
                    "VALUES (1, 'Role Check Merchant', true, :created_at, :created_at)"
                ),
                {"created_at": created_at},
            )
            with pytest.raises(DatabaseError):
                await connection.execute(
                    text(
                        "INSERT INTO merchant_members "
                        "(id, user_id, merchant_id, role, is_active, created_at, updated_at) "
                        "VALUES (1, 1, 1, 'OTHER', true, :created_at, :created_at)"
                    ),
                    {"created_at": created_at},
                )
    finally:
        await engine.dispose()


def test_identity_migration_creates_merchants_as_tenants(
    migrated_identity_database_url: str,
) -> None:
    columns = asyncio.run(read_table_columns(migrated_identity_database_url, "merchants"))

    assert {"id", "name", "is_active", "created_at", "updated_at"} <= columns


def test_identity_migration_enforces_unique_membership_per_tenant(
    migrated_identity_database_url: str,
) -> None:
    columns = asyncio.run(
        read_table_columns(migrated_identity_database_url, "merchant_members")
    )
    indexes, unique_indexes = asyncio.run(
        read_table_indexes(migrated_identity_database_url, "merchant_members")
    )
    foreign_keys = asyncio.run(
        read_table_foreign_keys(migrated_identity_database_url, "merchant_members")
    )

    assert {
        "id",
        "user_id",
        "merchant_id",
        "role",
        "is_active",
        "created_at",
        "updated_at",
    } <= columns
    assert ("merchant_id",) in indexes
    assert ("user_id",) in indexes
    assert ("user_id", "merchant_id") in unique_indexes
    assert foreign_keys == {
        ("user_id", "users", "id"),
        ("merchant_id", "merchants", "id"),
    }


def test_identity_migration_persists_revocable_refresh_sessions(
    migrated_identity_database_url: str,
) -> None:
    columns = asyncio.run(
        read_table_columns(migrated_identity_database_url, "auth_sessions")
    )
    indexes, unique_indexes = asyncio.run(
        read_table_indexes(migrated_identity_database_url, "auth_sessions")
    )
    foreign_keys = asyncio.run(
        read_table_foreign_keys(migrated_identity_database_url, "auth_sessions")
    )

    assert {
        "id",
        "user_id",
        "refresh_token_hash",
        "expires_at",
        "revoked_at",
        "revoked_reason",
        "replaced_by_session_id",
        "created_at",
        "updated_at",
    } <= columns
    assert "refresh_token" not in columns
    assert ("user_id",) in indexes
    assert ("refresh_token_hash",) in unique_indexes
    assert foreign_keys == {
        ("user_id", "users", "id"),
        ("replaced_by_session_id", "auth_sessions", "id"),
    }


def test_identity_migration_round_trips_session_expiry_as_utc(
    migrated_identity_database_url: str,
) -> None:
    expires_at = asyncio.run(
        persist_and_read_session_expiry(migrated_identity_database_url)
    )

    assert expires_at == datetime(2026, 8, 5, 12, tzinfo=UTC)
    assert expires_at.tzinfo is UTC
    assert expires_at > datetime(2026, 8, 5, 11, tzinfo=UTC)


def test_identity_migration_rejects_invalid_merchant_member_role(
    migrated_identity_database_url: str,
) -> None:
    asyncio.run(insert_invalid_merchant_member_role(migrated_identity_database_url))
