from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.merchants.models import Merchant
from app.shared.tenancy.context import Principal
from app.shared.tenancy.repositories import PlatformRepository


class PlatformMerchantRepository(PlatformRepository):
    """The only merchant repository permitted to list across tenant boundaries."""

    def __init__(self, *, session: AsyncSession, principal: Principal) -> None:
        super().__init__(session=session, principal=principal)

    async def list_all(self) -> list[Merchant]:
        result = await self._session.scalars(select(Merchant).order_by(Merchant.id))
        return list(result)
