import asyncio

import pytest

from app.modules.merchants.models import Merchant, MerchantMember, MerchantMemberRole
from app.shared.tenancy.context import (
    TenantAccessDenied,
    TenantContext,
    TenantContextFactory,
    _issue_principal,
)
from app.shared.tenancy.session import tenant_scope


class SequenceSession:
    def __init__(self, *results: object | None) -> None:
        self._results = list(results)

    async def scalar(self, statement: object) -> object | None:
        return self._results.pop(0)


def test_active_member_can_build_verified_tenant_context() -> None:
    member = MerchantMember(
        user_id=7,
        merchant_id=11,
        role=MerchantMemberRole.OWNER,
        is_active=True,
    )
    merchant = Merchant(id=11, name="Merchant A", is_active=True)
    factory = TenantContextFactory(session=SequenceSession(member, merchant))

    context = asyncio.run(
        factory.for_merchant(
            principal=_issue_principal(user_id=7, is_platform_admin=False),
            merchant_id=11,
        )
    )

    assert context.merchant_id == 11
    assert context.membership_role is MerchantMemberRole.OWNER


def test_member_cannot_build_context_for_another_merchant() -> None:
    factory = TenantContextFactory(session=SequenceSession(None))

    with pytest.raises(TenantAccessDenied):
        asyncio.run(
            factory.for_merchant(
                principal=_issue_principal(user_id=7, is_platform_admin=False),
                merchant_id=12,
            )
        )


def test_tenant_scope_rejects_a_forged_context() -> None:
    with pytest.raises(TenantAccessDenied):
        with tenant_scope(
            TenantContext(
                principal=_issue_principal(user_id=7, is_platform_admin=False),
                merchant_id=11,
                membership_role=MerchantMemberRole.OWNER,
            )
        ):
            pass
