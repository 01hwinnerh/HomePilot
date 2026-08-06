from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.models.tenant import MerchantOwnedMixin
from app.shared.tenancy.context import (
    PlatformAccessDenied,
    Principal,
    TenantAccessDenied,
    TenantContext,
    require_trusted_principal,
    require_trusted_tenant_context,
)

TenantModel = TypeVar("TenantModel", bound=MerchantOwnedMixin)


class TenantRepository[TenantModel]:
    """Repository that requires a verified context and always states its tenant filter."""

    def __init__(
        self,
        *,
        session: AsyncSession,
        context: TenantContext,
        model: type[TenantModel],
    ) -> None:
        require_trusted_tenant_context(context)
        self._session = session
        self._context = context
        self._model = model

    async def get_by_id(self, *, resource_id: int) -> TenantModel | None:
        statement = select(self._model).where(
            self._model.id == resource_id,
            self._model.merchant_id == self._context.merchant_id,
        )
        return await self._session.scalar(statement)


class PlatformRepository:
    """Base class for explicit cross-tenant reads available only to platform admins."""

    def __init__(self, *, session: AsyncSession, principal: Principal) -> None:
        try:
            require_trusted_principal(principal)
        except TenantAccessDenied as error:
            raise PlatformAccessDenied("Platform principal was not server-issued.") from error
        if not principal.is_platform_admin:
            raise PlatformAccessDenied("Platform administrator access is required.")
        self._session = session
        self._principal = principal
