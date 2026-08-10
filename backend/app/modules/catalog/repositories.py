from dataclasses import dataclass

from sqlalchemy import and_, exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import SKU, Category, Product, ProductStatus, Store
from app.modules.merchants.models import Merchant


@dataclass(frozen=True)
class PublicProductRecord:
    product: Product
    store: Store
    merchant: Merchant
    category: Category
    skus: list[SKU]


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

    async def list_active_categories(self) -> list[Category]:
        result = await self._session.scalars(
            select(Category)
            .where(Category.is_active.is_(True))
            .order_by(Category.sort_order, Category.id)
        )
        return list(result.all())

    def _public_product_statement(self):
        return (
            select(Product, Store, Merchant, Category)
            .join(
                Store,
                and_(
                    Store.id == Product.store_id,
                    Store.merchant_id == Product.merchant_id,
                    Store.is_active.is_(True),
                ),
            )
            .join(Merchant, Merchant.id == Product.merchant_id)
            .join(Category, Category.id == Product.category_id)
            .where(
                Product.status == ProductStatus.PUBLISHED,
                Merchant.is_active.is_(True),
                Category.is_active.is_(True),
                exists(
                    select(SKU.id).where(
                        SKU.product_id == Product.id,
                        SKU.merchant_id == Product.merchant_id,
                        SKU.is_active.is_(True),
                    )
                ),
            )
        )

    async def list_public_product_records_by_ids(
        self,
        *,
        product_ids: list[int],
    ) -> list[PublicProductRecord]:
        if not product_ids:
            return []
        statement = self._public_product_statement().where(Product.id.in_(product_ids))
        rows = (await self._session.execute(statement)).all()
        records: list[PublicProductRecord] = []
        for product, store, merchant, category in rows:
            skus = await self.list_active_skus(
                product_id=product.id,
                merchant_id=product.merchant_id,
            )
            records.append(
                PublicProductRecord(
                    product=product,
                    store=store,
                    merchant=merchant,
                    category=category,
                    skus=skus,
                )
            )
        order = {product_id: index for index, product_id in enumerate(product_ids)}
        records.sort(key=lambda record: order[record.product.id])
        return records

    async def get_public_product_record(self, *, product_id: int) -> PublicProductRecord | None:
        records = await self.list_public_product_records_by_ids(product_ids=[product_id])
        return records[0] if records else None

    async def get_published_product(self, *, product_id: int) -> Product | None:
        record = await self.get_public_product_record(product_id=product_id)
        return record.product if record is not None else None

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

    async def get_public_product_document(self, *, product_id: int) -> dict[str, object] | None:
        record = await self.get_public_product_record(product_id=product_id)
        if record is None:
            return None
        product, store, merchant, category, skus = (
            record.product,
            record.store,
            record.merchant,
            record.category,
            record.skus,
        )
        return {
            "product_id": str(product.id),
            "merchant_id": str(product.merchant_id),
            "store_id": str(product.store_id),
            "merchant_name": merchant.name,
            "store_name": store.name,
            "store_slug": store.slug,
            "category_id": str(category.id),
            "category_path": category.slug,
            "name": product.name,
            "description": product.description,
            "active_skus": [
                {
                    "sku_id": str(sku.id),
                    "sku_name": sku.sku_name,
                    "variant_attributes": sku.variant_attributes,
                    "price_minor": sku.price_minor,
                    "currency": sku.currency,
                }
                for sku in skus
            ],
            "min_price_minor": min(sku.price_minor for sku in skus),
            "currency": skus[0].currency,
        }
