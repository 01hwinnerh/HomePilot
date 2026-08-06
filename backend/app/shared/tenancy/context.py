from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.merchants.models import Merchant, MerchantMember, MerchantMemberRole


class TenantAccessDenied(PermissionError):
    """Raised when a principal cannot act within the requested merchant tenant."""


class PlatformAccessDenied(PermissionError):
    """Raised when a non-platform principal requests a platform-only operation."""


_PRINCIPAL_CAPABILITY = object()
_TENANT_CONTEXT_CAPABILITY = object()


@dataclass(frozen=True)
class Principal:
    """A server-verified authenticated identity without tenant claims."""

    user_id: int
    is_platform_admin: bool
    _capability: object | None = field(default=None, repr=False, compare=False)


@dataclass(frozen=True)
class TenantContext:
    """A principal's verified active membership in exactly one merchant."""

    principal: Principal
    merchant_id: int
    membership_role: MerchantMemberRole
    _capability: object | None = field(default=None, repr=False, compare=False)


def _issue_principal(*, user_id: int, is_platform_admin: bool) -> Principal:
    """Create the capability-bearing identity used by trusted server-side boundaries."""

    return Principal(
        user_id=user_id,
        is_platform_admin=is_platform_admin,
        _capability=_PRINCIPAL_CAPABILITY,
    )


def require_trusted_principal(principal: Principal) -> None:
    """Reject a dataclass created from untrusted request or model parameters."""

    if principal._capability is not _PRINCIPAL_CAPABILITY:
        raise TenantAccessDenied("Principal was not issued by a trusted identity boundary.")


def require_trusted_tenant_context(context: TenantContext) -> None:
    """Reject a tenant context not issued by the membership factory."""

    if context._capability is not _TENANT_CONTEXT_CAPABILITY:
        raise TenantAccessDenied("Tenant context was not issued by the membership factory.")


class TenantContextFactory:
    """Builds trusted tenant contexts only from active database relationships."""

    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def for_merchant(
        self,
        *,
        principal: Principal,
        merchant_id: int,
    ) -> TenantContext:
        require_trusted_principal(principal)
        membership = await self._session.scalar(
            select(MerchantMember).where(
                MerchantMember.user_id == principal.user_id,
                MerchantMember.merchant_id == merchant_id,
                MerchantMember.is_active.is_(True),
            )
        )
        if membership is None:
            raise TenantAccessDenied("No active membership for this merchant.")

        merchant = await self._session.scalar(
            select(Merchant).where(
                Merchant.id == merchant_id,
                Merchant.is_active.is_(True),
            )
        )
        if merchant is None:
            raise TenantAccessDenied("Merchant is not active.")

        return TenantContext(
            principal=principal,
            merchant_id=merchant_id,
            membership_role=membership.role,
            _capability=_TENANT_CONTEXT_CAPABILITY,
        )
