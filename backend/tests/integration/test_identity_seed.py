import asyncio

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.security import verify_password
from app.modules.identity.demo_seed import (
    DEMO_MERCHANT_A_NAME,
    DEMO_MERCHANT_B_NAME,
    DEMO_MERCHANT_OWNER_A_EMAIL,
    DEMO_MERCHANT_OWNER_B_EMAIL,
    DEMO_PLATFORM_ADMIN_EMAIL,
    DemoSeedConflictError,
    seed_identity_demo_data,
)
from app.modules.identity.models import User
from app.modules.merchants.models import Merchant, MerchantMember, MerchantMemberRole


def test_seed_creates_minimum_demo_identities(
    migrated_identity_database_url: str,
) -> None:
    asyncio.run(_seed_creates_minimum_demo_identities(migrated_identity_database_url))


def test_seed_is_idempotent(migrated_identity_database_url: str) -> None:
    asyncio.run(_seed_is_idempotent(migrated_identity_database_url))


def test_seed_rejects_conflicting_existing_demo_identifier(
    migrated_identity_database_url: str,
) -> None:
    asyncio.run(_seed_rejects_conflicting_existing_demo_identifier(migrated_identity_database_url))


def test_seed_migrates_legacy_demo_email_to_standard_domain(
    migrated_identity_database_url: str,
) -> None:
    asyncio.run(_seed_migrates_legacy_demo_email_to_standard_domain(migrated_identity_database_url))


async def _seed_creates_minimum_demo_identities(database_url: str) -> None:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            await seed_identity_demo_data(session, password="safe-demo-password-123")
            await session.commit()

            users = list(
                (
                    await session.scalars(
                        select(User).where(
                            User.email.in_(
                                [
                                    DEMO_PLATFORM_ADMIN_EMAIL,
                                    DEMO_MERCHANT_OWNER_A_EMAIL,
                                    DEMO_MERCHANT_OWNER_B_EMAIL,
                                ]
                            )
                        )
                    )
                ).all()
            )
            merchants = list(
                (
                    await session.scalars(
                        select(Merchant).where(
                            Merchant.name.in_(
                                [DEMO_MERCHANT_A_NAME, DEMO_MERCHANT_B_NAME]
                            )
                        )
                    )
                ).all()
            )
            memberships = list((await session.scalars(select(MerchantMember))).all())

        assert len(users) == 3
        assert await _count_demo_users(session_factory) == 3
        assert all(user.is_active for user in users)
        assert all(verify_password("safe-demo-password-123", user.password_hash) for user in users)

        platform_admin = next(user for user in users if user.email == DEMO_PLATFORM_ADMIN_EMAIL)
        assert platform_admin.is_platform_admin is True
        assert len(merchants) == 2
        assert all(merchant.is_active for merchant in merchants)
        assert len(memberships) == 2
        assert {membership.role for membership in memberships} == {MerchantMemberRole.OWNER}
        assert {membership.merchant_id for membership in memberships} == {
            merchant.id for merchant in merchants
        }
        assert len({membership.user_id for membership in memberships}) == 2
    finally:
        await engine.dispose()


async def _seed_is_idempotent(database_url: str) -> None:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            await seed_identity_demo_data(session, password="safe-demo-password-123")
            await session.commit()
            await seed_identity_demo_data(session, password="safe-demo-password-123")
            await session.commit()

        async with session_factory() as session:
            user_count = await session.scalar(
                select(func.count())
                .select_from(User)
                .where(
                    User.email.in_(
                        [
                            DEMO_PLATFORM_ADMIN_EMAIL,
                            DEMO_MERCHANT_OWNER_A_EMAIL,
                            DEMO_MERCHANT_OWNER_B_EMAIL,
                        ]
                    )
                )
            )
            merchant_count = await session.scalar(
                select(func.count())
                .select_from(Merchant)
                .where(Merchant.name.in_([DEMO_MERCHANT_A_NAME, DEMO_MERCHANT_B_NAME]))
            )
            membership_count = await session.scalar(
                select(func.count()).select_from(MerchantMember)
            )

        assert user_count == 3
        assert merchant_count == 2
        assert membership_count == 2
    finally:
        await engine.dispose()


async def _seed_rejects_conflicting_existing_demo_identifier(database_url: str) -> None:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            session.add(
                User(
                    email=DEMO_PLATFORM_ADMIN_EMAIL,
                    password_hash="ordinary-user-password-hash",
                    is_active=True,
                    is_platform_admin=False,
                )
            )
            await session.commit()

            with pytest.raises(DemoSeedConflictError, match="platform administrator"):
                await seed_identity_demo_data(session, password="safe-demo-password-123")

        async with session_factory() as session:
            users = list((await session.scalars(select(User))).all())
            assert len(users) == 1
            assert users[0].password_hash == "ordinary-user-password-hash"
            assert users[0].is_platform_admin is False
    finally:
        await engine.dispose()


async def _seed_migrates_legacy_demo_email_to_standard_domain(database_url: str) -> None:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            session.add(
                User(
                    email="platform.admin@homepilot.local",
                    password_hash="legacy-demo-password-hash",
                    is_active=True,
                    is_platform_admin=True,
                )
            )
            await session.commit()

            await seed_identity_demo_data(session, password="safe-demo-password-123")
            await session.commit()

        async with session_factory() as session:
            emails = set((await session.scalars(select(User.email))).all())
            assert "platform.admin@homepilot.dev" in emails
            assert "platform.admin@homepilot.local" not in emails
    finally:
        await engine.dispose()


async def _count_demo_users(session_factory: async_sessionmaker) -> int:
    async with session_factory() as session:
        return await session.scalar(select(func.count()).select_from(User)) or 0
