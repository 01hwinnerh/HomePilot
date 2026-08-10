from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.modules.catalog.repositories import PublicCatalogRepository
from app.modules.catalog.schemas import PublicProductResponse, PublicSKUResponse

router = APIRouter(prefix="/catalog", tags=["catalog"])


async def _public_product_response(
    repository: PublicCatalogRepository,
    product,
) -> PublicProductResponse:
    skus = await repository.list_active_skus(
        product_id=product.id,
        merchant_id=product.merchant_id,
    )
    return PublicProductResponse(
        id=product.id,
        store_id=product.store_id,
        name=product.name,
        description=product.description,
        skus=[PublicSKUResponse.model_validate(sku) for sku in skus],
    )


@router.get("/products", response_model=list[PublicProductResponse])
async def list_public_products(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[PublicProductResponse]:
    repository = PublicCatalogRepository(session=session)
    products = await repository.list_published_products(offset=offset, limit=limit)
    return [await _public_product_response(repository, product) for product in products]


@router.get("/products/{product_id}", response_model=PublicProductResponse)
async def get_public_product(
    product_id: int,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PublicProductResponse:
    repository = PublicCatalogRepository(session=session)
    product = await repository.get_published_product(product_id=product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return await _public_product_response(repository, product)
