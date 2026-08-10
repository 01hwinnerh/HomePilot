from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import SKU, Product, ProductStatus, Store
from app.modules.merchants.models import Merchant


class PublicCatalogRepository:
    """Read-only public catalog queries with publication and active-state filters."""

    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def list_published_products(
        self,
        *,
        offset: int,
        limit: int,
    ) -> list[Product]:
        statement = (
            select(Product)
            .join(
                Store,
                and_(
                    Store.id == Product.store_id,
                    Store.merchant_id == Product.merchant_id,
                    Store.is_active.is_(True),
                ),
            )
            .join(Merchant, Merchant.id == Product.merchant_id)
            .where(
                Product.status == ProductStatus.PUBLISHED,
                Merchant.is_active.is_(True),
            )
            .order_by(Product.created_at.desc(), Product.id.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.scalars(statement)
        return list(result.all())

    async def get_published_product(self, *, product_id: int) -> Product | None:
        statement = (
            select(Product)
            .join(
                Store,
                and_(
                    Store.id == Product.store_id,
                    Store.merchant_id == Product.merchant_id,
                    Store.is_active.is_(True),
                ),
            )
            .join(Merchant, Merchant.id == Product.merchant_id)
            .where(
                Product.id == product_id,
                Product.status == ProductStatus.PUBLISHED,
                Merchant.is_active.is_(True),
            )
        )
        return await self._session.scalar(statement)

    async def list_active_skus(self, *, product_id: int, merchant_id: int) -> list[SKU]:
        statement = (
            select(SKU)
            .where(
                SKU.product_id == product_id,
                SKU.merchant_id == merchant_id,
                SKU.is_active.is_(True),
            )
            .order_by(SKU.id)
        )
        result = await self._session.scalars(statement)
        return list(result.all())
