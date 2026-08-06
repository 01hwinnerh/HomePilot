from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache

from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.shared.tenancy import session as tenancy_session  # noqa: F401


class UnsafeTestDatabaseError(ValueError):
    """Raised before a test can operate on an unsafe database target."""


def validate_test_database_isolation(*, database_url: str, test_database_url: str) -> None:
    """Reject a test target that is not visibly isolated from business data."""

    business_database = make_url(database_url).database
    test_database = make_url(test_database_url).database
    if (
        business_database is not None
        and test_database is not None
        and business_database.casefold() == test_database.casefold()
    ):
        raise UnsafeTestDatabaseError(
            "TEST_DATABASE_URL database name must differ from DATABASE_URL."
        )
    if test_database is None or "test" not in test_database.casefold():
        raise UnsafeTestDatabaseError(
            "TEST_DATABASE_URL database name must contain 'test'."
        )


class Database:
    """Owns the async SQLAlchemy engine and session lifecycle."""

    def __init__(self, url: str) -> None:
        self.engine: AsyncEngine = create_async_engine(
            url,
            pool_pre_ping=True,
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    async def dispose(self) -> None:
        await self.engine.dispose()


@lru_cache
def get_database() -> Database:
    """Return the application database owner configured for this process."""

    return Database(get_settings().database_url)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency that scopes an async database session to one request."""

    database = get_database()
    async with database.session() as session:
        yield session


async def close_database() -> None:
    """Dispose the cached engine when the FastAPI process is shutting down."""

    database = get_database()
    await database.dispose()
    get_database.cache_clear()
