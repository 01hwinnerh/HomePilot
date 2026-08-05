import asyncio
from collections.abc import AsyncIterator
from uuid import uuid4

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.database import get_db_session
from app.main import app


def test_login_attempts_are_rate_limited_by_real_redis(
    migrated_identity_database_url: str,
) -> None:
    asyncio.run(_run_rate_limit_check(migrated_identity_database_url))


async def _run_rate_limit_check(database_url: str) -> None:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    settings = get_settings()
    email = f"rate-{uuid4().hex}@example.com"

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_get_db_session
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            for _ in range(settings.auth_rate_limit_max_attempts):
                response = await client.post(
                    "/api/v1/auth/login",
                    json={"email": email, "password": "not-the-right-password"},
                )
                assert response.status_code == 401

            blocked = await client.post(
                "/api/v1/auth/login",
                json={"email": email, "password": "not-the-right-password"},
            )
            assert blocked.status_code == 429
            assert blocked.json() == {"detail": "Too many authentication attempts"}
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
