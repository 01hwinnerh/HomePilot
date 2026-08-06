import pytest

from app.modules.merchants.models import MerchantMember, MerchantMemberRole
from app.modules.merchants.repositories import PlatformMerchantRepository
from app.shared.tenancy.context import (
    PlatformAccessDenied,
    Principal,
    TenantAccessDenied,
    TenantContext,
    _issue_principal,
)
from app.shared.tenancy.repositories import TenantRepository


def test_tenant_repository_rejects_a_forged_context() -> None:
    with pytest.raises(TenantAccessDenied):
        TenantRepository(
            session=object(),
            context=TenantContext(
                principal=Principal(user_id=7, is_platform_admin=False),
                merchant_id=11,
                membership_role=MerchantMemberRole.OWNER,
            ),
            model=MerchantMember,
        )


def test_platform_repository_rejects_a_non_platform_principal() -> None:
    with pytest.raises(PlatformAccessDenied):
        PlatformMerchantRepository(
            session=object(),
            principal=_issue_principal(user_id=7, is_platform_admin=False),
        )


def test_platform_repository_rejects_a_forged_platform_flag() -> None:
    with pytest.raises(PlatformAccessDenied):
        PlatformMerchantRepository(
            session=object(),
            principal=Principal(user_id=7, is_platform_admin=True),
        )
