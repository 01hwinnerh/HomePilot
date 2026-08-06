import asyncio

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.api.v1.dependencies import (
    get_current_principal,
    get_tenant_context,
    require_platform_principal,
)
from app.core.config import get_settings
from app.core.security import create_access_token
from app.modules.identity.models import User
from app.modules.merchants.models import Merchant, MerchantMember, MerchantMemberRole
from app.modules.merchants.repositories import PlatformMerchantRepository
from app.shared.tenancy.context import TenantContext
from app.shared.tenancy.repositories import TenantRepository
from app.shared.tenancy.session import current_tenant_context, tenant_scope


def test_tenant_context_and_repository_prevent_cross_merchant_access(
    migrated_identity_database_url: str,
) -> None:
    asyncio.run(_assert_tenant_isolation(migrated_identity_database_url))


async def _assert_tenant_isolation(database_url: str) -> None:
    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            member_a, member_b, user_a, platform_user = await _create_tenant_data(session)
            token = create_access_token(user_id=user_a.id, settings=get_settings())
            resolved_principal = await get_current_principal(
                credentials=HTTPAuthorizationCredentials(scheme="Bearer", credentials=token),
                db_session=session,
            )
            context_a = await get_tenant_context(
                merchant_id=member_a.merchant_id,
                principal=resolved_principal,
                db_session=session,
            )
            with pytest.raises(HTTPException, match="Merchant access denied") as denied:
                await get_tenant_context(
                    merchant_id=member_b.merchant_id,
                    principal=resolved_principal,
                    db_session=session,
                )
            assert denied.value.status_code == 403
            user_b_token = create_access_token(user_id=member_b.user_id, settings=get_settings())
            principal_b = await get_current_principal(
                credentials=HTTPAuthorizationCredentials(
                    scheme="Bearer",
                    credentials=user_b_token,
                ),
                db_session=session,
            )
            context_b = await get_tenant_context(
                merchant_id=member_b.merchant_id,
                principal=principal_b,
                db_session=session,
            )

            with tenant_scope(context_a):
                direct_result = await session.scalar(
                    select(MerchantMember).where(MerchantMember.id == member_b.id)
                )
                repository_result = await TenantRepository(
                    session=session,
                    context=context_a,
                    model=MerchantMember,
                ).get_by_id(resource_id=member_b.id)
                dml_result = await session.execute(
                    update(MerchantMember)
                    .where(MerchantMember.id == member_b.id)
                    .values(is_active=False)
                )
                delete_result = await session.execute(
                    delete(MerchantMember).where(MerchantMember.id == member_b.id)
                )
            assert direct_result is None
            assert repository_result is None
            assert dml_result.rowcount == 0
            assert delete_result.rowcount == 0

            with pytest.raises(RuntimeError, match="force scope cleanup"):
                with tenant_scope(context_a):
                    raise RuntimeError("force scope cleanup")

            async def read_merchant_id_from_scope(context: TenantContext) -> int:
                with tenant_scope(context):
                    await asyncio.sleep(0)
                    current_context = current_tenant_context()
                    assert current_context is not None
                    return current_context.merchant_id

            scoped_merchant_ids = await asyncio.gather(
                read_merchant_id_from_scope(context_a),
                read_merchant_id_from_scope(context_b),
            )
            assert scoped_merchant_ids == [member_a.merchant_id, member_b.merchant_id]

            unscoped_result = await session.scalar(
                select(MerchantMember).where(MerchantMember.id == member_b.id)
            )
            assert unscoped_result is not None

            platform_token = create_access_token(user_id=platform_user.id, settings=get_settings())
            platform_principal = await get_current_principal(
                credentials=HTTPAuthorizationCredentials(
                    scheme="Bearer",
                    credentials=platform_token,
                ),
                db_session=session,
            )
            platform_repository = PlatformMerchantRepository(
                session=session,
                principal=await require_platform_principal(principal=platform_principal),
            )
            assert len(await platform_repository.list_all()) == 2
            assert resolved_principal.user_id == user_a.id
            assert resolved_principal.is_platform_admin is False
    finally:
        await engine.dispose()


async def _create_tenant_data(session: object) -> tuple[MerchantMember, MerchantMember, User, User]:
    user_a = User(email="tenant-a@example.com", password_hash="hash", is_active=True)
    user_b = User(email="tenant-b@example.com", password_hash="hash", is_active=True)
    platform_user = User(
        email="platform@example.com",
        password_hash="hash",
        is_active=True,
        is_platform_admin=True,
    )
    merchant_a = Merchant(name="Merchant A", is_active=True)
    merchant_b = Merchant(name="Merchant B", is_active=True)
    session.add_all([user_a, user_b, platform_user, merchant_a, merchant_b])
    await session.flush()
    member_a = MerchantMember(
        user_id=user_a.id,
        merchant_id=merchant_a.id,
        role=MerchantMemberRole.OWNER,
        is_active=True,
    )
    member_b = MerchantMember(
        user_id=user_b.id,
        merchant_id=merchant_b.id,
        role=MerchantMemberRole.OWNER,
        is_active=True,
    )
    session.add_all([member_a, member_b])
    await session.commit()
    return member_a, member_b, user_a, platform_user
