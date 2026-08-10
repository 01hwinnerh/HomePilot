from collections.abc import AsyncIterator
from typing import Annotated

from elasticsearch import AsyncElasticsearch
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.modules.catalog.repositories import PublicCatalogRepository, PublicProductRecord
from app.modules.catalog.schemas import (
    CategoryResponse,
    PublicProductResponse,
    PublicSKUResponse,
)
from app.modules.catalog.search.contracts import CatalogSearchPort
from app.modules.catalog.search.elasticsearch import ElasticsearchCatalogSearch
from app.modules.catalog.search.service import CatalogSearchService, SearchUnavailable

router = APIRouter(prefix="/catalog", tags=["catalog"])


async def get_catalog_search() -> AsyncIterator[CatalogSearchPort]:
    settings = get_settings()
    client = AsyncElasticsearch(
        settings.elasticsearch_url,
        request_timeout=settings.elasticsearch_request_timeout_seconds,
        max_retries=settings.elasticsearch_max_retries,
        retry_on_timeout=True,
    )
    try:
        yield ElasticsearchCatalogSearch(
            client=client,
            index_alias=settings.elasticsearch_index_alias,
        )
    finally:
        await client.close()


def _public_product_response(record: PublicProductRecord) -> PublicProductResponse:
    product = record.product
    return PublicProductResponse(
        id=product.id,
        merchant_id=product.merchant_id,
        merchant_name=record.merchant.name,
        store_id=product.store_id,
        store_name=record.store.name,
        store_slug=record.store.slug,
        category_id=product.category_id,
        category_name=record.category.name,
        name=product.name,
        description=product.description,
        skus=[PublicSKUResponse.model_validate(sku) for sku in record.skus],
    )


@router.get("/categories", response_model=list[CategoryResponse])
async def list_public_categories(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[CategoryResponse]:
    categories = await PublicCatalogRepository(session=session).list_active_categories()
    return [CategoryResponse.model_validate(category) for category in categories]


@router.get("/products", response_model=list[PublicProductResponse])
async def list_public_products(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    search: Annotated[CatalogSearchPort, Depends(get_catalog_search)],
    q: str | None = Query(default=None, min_length=1, max_length=200),
    category_id: int | None = Query(default=None, gt=0),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[PublicProductResponse]:
    repository = PublicCatalogRepository(session=session)
    if q is None and category_id is None:
        products = await repository.list_published_products(offset=offset, limit=limit)
        records = await repository.list_public_product_records_by_ids(
            product_ids=[product.id for product in products]
        )
        return [_public_product_response(record) for record in records]
    try:
        records = await CatalogSearchService(repository=repository, search=search).search(
            query=q,
            category_id=category_id,
            offset=offset,
            limit=limit,
        )
    except SearchUnavailable as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SEARCH_UNAVAILABLE",
        ) from error
    return [_public_product_response(record) for record in records]


@router.get("/products/{product_id}", response_model=PublicProductResponse)
async def get_public_product(
    product_id: int,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PublicProductResponse:
    record = await PublicCatalogRepository(session=session).get_public_product_record(
        product_id=product_id
    )
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return _public_product_response(record)
