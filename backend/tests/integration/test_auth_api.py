import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.v1.auth import get_auth_rate_limiter
from app.core.database import get_db_session
from app.main import app
from app.modules.identity.models import AuthSession, User
from app.modules.merchants.models import Merchant, MerchantMember, MerchantMemberRole


class NoOpRateLimiter:
    async def check(self, *, scope: str, identity: str, client_ip: str) -> None:
        return None


def test_customer_can_register_then_read_current_identity(
    migrated_identity_database_url: str,
) -> None:
    asyncio.run(_register_then_read_current_identity(migrated_identity_database_url))


def test_refresh_rotates_cookie_session_and_rejects_replay(
    migrated_identity_database_url: str,
) -> None:
    asyncio.run(_refresh_rotates_cookie_session(migrated_identity_database_url))


def test_refresh_and_logout_require_csrf_and_logout_revokes_session(
    migrated_identity_database_url: str,
) -> None:
    asyncio.run(_csrf_protects_cookie_authenticated_routes(migrated_identity_database_url))


def test_concurrent_refresh_allows_only_one_rotation(
    migrated_identity_database_url: str,
) -> None:
    asyncio.run(_concurrent_refresh_allows_only_one_rotation(migrated_identity_database_url))


def test_me_returns_only_enabled_merchant_memberships(
    migrated_identity_database_url: str,
) -> None:
    asyncio.run(_me_returns_enabled_memberships(migrated_identity_database_url))


def test_inactive_user_cannot_refresh_or_read_current_identity(
    migrated_identity_database_url: str,
) -> None:
    asyncio.run(_inactive_user_is_rejected(migrated_identity_database_url))


async def _register_then_read_current_identity(database_url: str) -> None:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_auth_rate_limiter] = NoOpRateLimiter
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            unauthenticated = await client.get("/api/v1/auth/me")
            assert unauthenticated.status_code == 401

            response = await client.post(
                "/api/v1/auth/register",
                json={"email": "buyer@example.com", "password": "safe-password-123"},
            )

            assert response.status_code == 201
            assert response.json()["token_type"] == "bearer"
            assert response.json()["user"]["memberships"] == []
            set_cookies = response.headers.get_list("set-cookie")
            assert "HttpOnly" in set_cookies[0]
            assert "refresh_token=" in set_cookies[0]
            assert "Path=/api/v1/auth" in set_cookies[0]
            assert "SameSite=lax" in set_cookies[0]
            assert "csrf_token=" in set_cookies[1]
            assert "HttpOnly" not in set_cookies[1]

            current_user = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {response.json()['access_token']}"},
            )
            assert current_user.status_code == 200
            assert current_user.json()["email"] == "buyer@example.com"
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def _refresh_rotates_cookie_session(database_url: str) -> None:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_auth_rate_limiter] = NoOpRateLimiter
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            registered = await client.post(
                "/api/v1/auth/register",
                json={"email": "rotate@example.com", "password": "safe-password-123"},
            )
            assert registered.status_code == 201
            old_refresh_token = client.cookies.get("refresh_token")
            old_csrf_token = client.cookies.get("csrf_token")
            assert old_refresh_token is not None
            assert old_csrf_token is not None

            refreshed = await client.post(
                "/api/v1/auth/refresh",
                headers={"X-CSRF-Token": old_csrf_token},
            )
            assert refreshed.status_code == 200
            assert client.cookies.get("refresh_token") != old_refresh_token

        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as replay:
            replayed = await replay.post(
                "/api/v1/auth/refresh",
                headers={
                    "Cookie": f"refresh_token={old_refresh_token}; csrf_token={old_csrf_token}",
                    "X-CSRF-Token": old_csrf_token,
                },
            )
            assert replayed.status_code == 401
            assert replayed.json() == {"detail": "Invalid credentials"}
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def _csrf_protects_cookie_authenticated_routes(database_url: str) -> None:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_auth_rate_limiter] = NoOpRateLimiter
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            registered = await client.post(
                "/api/v1/auth/register",
                json={"email": "logout@example.com", "password": "safe-password-123"},
            )
            assert registered.status_code == 201
            refresh_token = client.cookies.get("refresh_token")
            csrf_token = client.cookies.get("csrf_token")
            assert refresh_token is not None
            assert csrf_token is not None

            missing_csrf = await client.post("/api/v1/auth/refresh")
            assert missing_csrf.status_code == 403
            wrong_refresh_csrf = await client.post(
                "/api/v1/auth/refresh",
                headers={"X-CSRF-Token": "wrong-token"},
            )
            assert wrong_refresh_csrf.status_code == 403
            wrong_logout_csrf = await client.post(
                "/api/v1/auth/logout",
                headers={"X-CSRF-Token": "wrong-token"},
            )
            assert wrong_logout_csrf.status_code == 403
            missing_logout_csrf = await client.post("/api/v1/auth/logout")
            assert missing_logout_csrf.status_code == 403

            logout = await client.post(
                "/api/v1/auth/logout",
                headers={"X-CSRF-Token": csrf_token},
            )
            assert logout.status_code == 204
            assert "Max-Age=0" in " ".join(logout.headers.get_list("set-cookie"))

        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as replay:
            rejected = await replay.post(
                "/api/v1/auth/refresh",
                headers={
                    "Cookie": f"refresh_token={refresh_token}; csrf_token={csrf_token}",
                    "X-CSRF-Token": csrf_token,
                },
            )
            assert rejected.status_code == 401
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def _concurrent_refresh_allows_only_one_rotation(database_url: str) -> None:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_auth_rate_limiter] = NoOpRateLimiter
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            registered = await client.post(
                "/api/v1/auth/register",
                json={"email": "concurrent@example.com", "password": "safe-password-123"},
            )
            assert registered.status_code == 201
            refresh_token = client.cookies.get("refresh_token")
            csrf_token = client.cookies.get("csrf_token")
            assert refresh_token is not None
            assert csrf_token is not None

        async def refresh_once() -> int:
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://testserver",
            ) as client:
                response = await client.post(
                    "/api/v1/auth/refresh",
                    headers={
                        "Cookie": f"refresh_token={refresh_token}; csrf_token={csrf_token}",
                        "X-CSRF-Token": csrf_token,
                    },
                )
                return response.status_code

        outcomes = await asyncio.gather(refresh_once(), refresh_once())
        assert sorted(outcomes) == [200, 401]
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def _me_returns_enabled_memberships(database_url: str) -> None:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_auth_rate_limiter] = NoOpRateLimiter
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            registered = await client.post(
                "/api/v1/auth/register",
                json={"email": "member@example.com", "password": "safe-password-123"},
            )
            assert registered.status_code == 201
            user_id = registered.json()["user"]["id"]

            async with session_factory() as session:
                active_merchant = Merchant(name="Active merchant", is_active=True)
                inactive_merchant = Merchant(name="Inactive merchant", is_active=False)
                session.add_all([active_merchant, inactive_merchant])
                await session.flush()
                session.add_all(
                    [
                        MerchantMember(
                            user_id=user_id,
                            merchant_id=active_merchant.id,
                            role=MerchantMemberRole.OWNER,
                            is_active=True,
                        ),
                        MerchantMember(
                            user_id=user_id,
                            merchant_id=inactive_merchant.id,
                            role=MerchantMemberRole.STAFF,
                            is_active=True,
                        ),
                    ]
                )
                await session.commit()

            current_user = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {registered.json()['access_token']}"},
            )
            assert current_user.status_code == 200
            assert current_user.json()["memberships"] == [
                {
                    "merchant_id": active_merchant.id,
                    "merchant_name": "Active merchant",
                    "role": "OWNER",
                }
            ]
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


async def _inactive_user_is_rejected(database_url: str) -> None:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db_session() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_auth_rate_limiter] = NoOpRateLimiter
    try:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            registered = await client.post(
                "/api/v1/auth/register",
                json={"email": "inactive@example.com", "password": "safe-password-123"},
            )
            assert registered.status_code == 201
            user_id = registered.json()["user"]["id"]
            refresh_token = client.cookies.get("refresh_token")
            csrf_token = client.cookies.get("csrf_token")
            assert refresh_token is not None
            assert csrf_token is not None

            async with session_factory() as session:
                await session.execute(
                    update(User).where(User.id == user_id).values(is_active=False)
                )
                await session.commit()

            current_user = await client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {registered.json()['access_token']}"},
            )
            assert current_user.status_code == 401
            refreshed = await client.post(
                "/api/v1/auth/refresh",
                headers={"X-CSRF-Token": csrf_token},
            )
            assert refreshed.status_code == 401

            async with session_factory() as session:
                await session.execute(
                    update(AuthSession)
                    .where(AuthSession.user_id == user_id)
                    .values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
                )
                await session.commit()
            expired = await client.post(
                "/api/v1/auth/refresh",
                headers={"X-CSRF-Token": csrf_token},
            )
            assert expired.status_code == 401
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()
