from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import SKU, Category, Product, ProductStatus, Store
from app.shared.outbox import append_event
from app.shared.tenancy.context import TenantContext, require_trusted_tenant_context


class CatalogNotFound(ValueError):
    """Raised when a resource is absent from the current merchant scope."""


class CatalogConflict(ValueError):
    """Raised when a catalog uniqueness or state conflict occurs."""


class InvalidCatalogState(ValueError):
    """Raised when a requested catalog state transition is invalid."""


class CatalogService:
    """Coordinates tenant-scoped catalog writes and lifecycle transitions."""

    def __init__(self, *, session: AsyncSession, context: TenantContext) -> None:
        require_trusted_tenant_context(context)
        self._session = session
        self._merchant_id = context.merchant_id

    async def create_store(self, *, name: str, slug: str) -> Store:
        store = Store(merchant_id=self._merchant_id, name=name, slug=slug)
        self._session.add(store)
        return await self._commit_created(store)

    async def get_store(self, *, store_id: int) -> Store:
        store = await self._session.scalar(
            select(Store).where(
                Store.id == store_id,
                Store.merchant_id == self._merchant_id,
            )
        )
        if store is None:
            raise CatalogNotFound("Store not found")
        return store

    async def list_stores(self, *, offset: int, limit: int) -> list[Store]:
        result = await self._session.scalars(
            select(Store)
            .where(Store.merchant_id == self._merchant_id)
            .order_by(Store.created_at.desc(), Store.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.all())

    async def list_products(
        self,
        *,
        category_id: int | None,
        product_status: ProductStatus | None,
        offset: int,
        limit: int,
    ) -> list[Product]:
        conditions = [Product.merchant_id == self._merchant_id]
        if category_id is not None:
            conditions.append(Product.category_id == category_id)
        if product_status is not None:
            conditions.append(Product.status == product_status)
        result = await self._session.scalars(
            select(Product)
            .where(*conditions)
            .order_by(Product.created_at.desc(), Product.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.all())

    async def list_skus(self, *, product_id: int, offset: int, limit: int) -> list[SKU]:
        await self.get_product(product_id=product_id)
        result = await self._session.scalars(
            select(SKU)
            .where(
                SKU.merchant_id == self._merchant_id,
                SKU.product_id == product_id,
            )
            .order_by(SKU.id)
            .offset(offset)
            .limit(limit)
        )
        return list(result.all())

    async def update_store(
        self,
        *,
        store_id: int,
        name: str | None = None,
        is_active: bool | None = None,
    ) -> Store:
        store = await self.get_store(store_id=store_id)
        if name is not None:
            store.name = name
        if is_active is not None:
            store.is_active = is_active
        self._append_catalog_event("catalog.store.changed", "store", store.id)
        await self._session.commit()
        return store

    async def create_product(
        self,
        *,
        store_id: int,
        category_id: int,
        name: str,
        description: str,
    ) -> Product:
        store = await self._session.scalar(
            select(Store).where(
                Store.id == store_id,
                Store.merchant_id == self._merchant_id,
            )
        )
        if store is None:
            await self._session.rollback()
            raise CatalogNotFound("Store not found")

        await self._require_active_leaf_category(category_id=category_id)

        product = Product(
            merchant_id=self._merchant_id,
            store_id=store_id,
            category_id=category_id,
            name=name,
            description=description,
            status=ProductStatus.DRAFT,
        )
        self._session.add(product)
        return await self._commit_created(product)

    async def get_product(self, *, product_id: int) -> Product:
        product = await self._session.scalar(
            select(Product).where(
                Product.id == product_id,
                Product.merchant_id == self._merchant_id,
            )
        )
        if product is None:
            raise CatalogNotFound("Product not found")
        return product

    async def update_product(
        self,
        *,
        product_id: int,
        category_id: int | None = None,
        name: str | None = None,
        description: str | None = None,
    ) -> Product:
        product = await self.get_product(product_id=product_id)
        if product.status is ProductStatus.ARCHIVED:
            raise InvalidCatalogState("Archived products cannot be edited")
        if category_id is not None:
            await self._require_active_leaf_category(category_id=category_id)
            product.category_id = category_id
        if name is not None:
            product.name = name
        if description is not None:
            product.description = description
        self._append_catalog_event("catalog.product.changed", "product", product.id)
        await self._session.commit()
        return product

    async def create_sku(
        self,
        *,
        product_id: int,
        sku_code: str,
        sku_name: str,
        variant_attributes: dict[str, object],
        price_minor: int,
        currency: str,
    ) -> SKU:
        product = await self._session.scalar(
            select(Product).where(
                Product.id == product_id,
                Product.merchant_id == self._merchant_id,
            )
        )
        if product is None:
            await self._session.rollback()
            raise CatalogNotFound("Product not found")

        duplicate = await self._session.scalar(
            select(SKU).where(
                SKU.merchant_id == self._merchant_id,
                SKU.sku_code == sku_code,
            )
        )
        if duplicate is not None:
            await self._session.rollback()
            raise CatalogConflict("SKU code already exists for this merchant")

        sku = SKU(
            merchant_id=self._merchant_id,
            product_id=product_id,
            sku_code=sku_code,
            sku_name=sku_name,
            variant_attributes=variant_attributes,
            price_minor=price_minor,
            currency=currency,
        )
        self._session.add(sku)
        return await self._commit_created(sku)

    async def get_sku(self, *, sku_id: int) -> SKU:
        sku = await self._session.scalar(
            select(SKU).where(
                SKU.id == sku_id,
                SKU.merchant_id == self._merchant_id,
            )
        )
        if sku is None:
            raise CatalogNotFound("SKU not found")
        return sku

    async def update_sku(
        self,
        *,
        sku_id: int,
        sku_name: str | None = None,
        variant_attributes: dict[str, object] | None = None,
        price_minor: int | None = None,
        is_active: bool | None = None,
    ) -> SKU:
        sku = await self.get_sku(sku_id=sku_id)
        if sku_name is not None:
            sku.sku_name = sku_name
        if variant_attributes is not None:
            sku.variant_attributes = variant_attributes
        if price_minor is not None:
            sku.price_minor = price_minor
        if is_active is not None:
            sku.is_active = is_active
        self._append_catalog_event("catalog.sku.changed", "product", sku.product_id)
        await self._session.commit()
        return sku

    async def publish_product(self, *, product_id: int) -> Product:
        product = await self._session.scalar(
            select(Product).where(
                Product.id == product_id,
                Product.merchant_id == self._merchant_id,
            )
        )
        if product is None:
            await self._session.rollback()
            raise CatalogNotFound("Product not found")
        if product.status is ProductStatus.ARCHIVED:
            await self._session.rollback()
            raise InvalidCatalogState("Archived products cannot be republished")

        store = await self._session.scalar(
            select(Store).where(
                Store.id == product.store_id,
                Store.merchant_id == self._merchant_id,
                Store.is_active.is_(True),
            )
        )
        active_sku = await self._session.scalar(
            select(SKU.id).where(
                SKU.product_id == product_id,
                SKU.merchant_id == self._merchant_id,
                SKU.is_active.is_(True),
            )
        )
        if store is None or active_sku is None:
            await self._session.rollback()
            raise InvalidCatalogState("Product requires an active store and SKU")

        product.status = ProductStatus.PUBLISHED
        self._append_catalog_event("catalog.product.changed", "product", product.id)
        await self._session.commit()
        return product

    async def archive_product(self, *, product_id: int) -> Product:
        product = await self._session.scalar(
            select(Product).where(
                Product.id == product_id,
                Product.merchant_id == self._merchant_id,
            )
        )
        if product is None:
            await self._session.rollback()
            raise CatalogNotFound("Product not found")
        product.status = ProductStatus.ARCHIVED
        self._append_catalog_event("catalog.product.changed", "product", product.id)
        await self._session.commit()
        return product

    async def _require_active_leaf_category(self, *, category_id: int) -> Category:
        category = await self._session.scalar(
            select(Category).where(
                Category.id == category_id,
                Category.is_active.is_(True),
            )
        )
        child = await self._session.scalar(
            select(Category.id).where(Category.parent_id == category_id)
        )
        if category is None or child is not None:
            await self._session.rollback()
            raise InvalidCatalogState("Product requires an active leaf category")
        return category

    async def _commit_created(self, instance: Store | Product | SKU) -> Store | Product | SKU:
        try:
            await self._session.flush()
            if isinstance(instance, Store):
                self._append_catalog_event("catalog.store.changed", "store", instance.id)
            elif isinstance(instance, Product):
                self._append_catalog_event("catalog.product.changed", "product", instance.id)
            else:
                self._append_catalog_event("catalog.sku.changed", "product", instance.product_id)
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise
        return instance

    def _append_catalog_event(
        self,
        event_type: str,
        aggregate_type: str,
        aggregate_id: int,
    ) -> None:
        append_event(
            self._session,
            event_type=event_type,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            payload={},
        )
