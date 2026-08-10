from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_db_session, scoped_tenant_context
from app.modules.catalog.schemas import (
    ProductCreate,
    ProductResponse,
    ProductUpdate,
    SKUCreate,
    SKUResponse,
    SKUUpdate,
    StoreCreate,
    StoreResponse,
    StoreUpdate,
)
from app.modules.catalog.service import (
    CatalogConflict,
    CatalogNotFound,
    CatalogService,
    InvalidCatalogState,
)
from app.shared.tenancy.context import TenantContext

router = APIRouter(prefix="/merchants/{merchant_id}", tags=["catalog"])


def _catalog_error(error: ValueError) -> HTTPException:
    if isinstance(error, CatalogNotFound):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, CatalogConflict):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))


def _service(session: AsyncSession, context: TenantContext) -> CatalogService:
    return CatalogService(session=session, context=context)


@router.post(
    "/stores",
    response_model=StoreResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_store(
    payload: StoreCreate,
    context: Annotated[TenantContext, Depends(scoped_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StoreResponse:
    try:
        result = await _service(session, context).create_store(
            name=payload.name,
            slug=payload.slug,
        )
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Store slug already exists for this merchant",
        ) from error
    return StoreResponse.model_validate(result)


@router.get("/stores/{store_id}", response_model=StoreResponse)
async def get_store(
    store_id: int,
    context: Annotated[TenantContext, Depends(scoped_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StoreResponse:
    try:
        result = await _service(session, context).get_store(store_id=store_id)
    except CatalogNotFound as error:
        raise _catalog_error(error) from error
    return StoreResponse.model_validate(result)


@router.patch("/stores/{store_id}", response_model=StoreResponse)
async def update_store(
    store_id: int,
    payload: StoreUpdate,
    context: Annotated[TenantContext, Depends(scoped_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> StoreResponse:
    try:
        result = await _service(session, context).update_store(
            store_id=store_id,
            name=payload.name,
            is_active=payload.is_active,
        )
    except (CatalogNotFound, InvalidCatalogState) as error:
        raise _catalog_error(error) from error
    return StoreResponse.model_validate(result)


@router.post(
    "/stores/{store_id}/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    store_id: int,
    payload: ProductCreate,
    context: Annotated[TenantContext, Depends(scoped_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProductResponse:
    if payload.store_id != store_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Store mismatch",
        )
    try:
        result = await _service(session, context).create_product(
            store_id=store_id,
            name=payload.name,
            description=payload.description,
        )
    except CatalogNotFound as error:
        raise _catalog_error(error) from error
    return ProductResponse.model_validate(result)


@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    context: Annotated[TenantContext, Depends(scoped_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProductResponse:
    try:
        result = await _service(session, context).get_product(product_id=product_id)
    except CatalogNotFound as error:
        raise _catalog_error(error) from error
    return ProductResponse.model_validate(result)


@router.patch("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    payload: ProductUpdate,
    context: Annotated[TenantContext, Depends(scoped_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProductResponse:
    try:
        result = await _service(session, context).update_product(
            product_id=product_id,
            name=payload.name,
            description=payload.description,
        )
    except (CatalogNotFound, InvalidCatalogState) as error:
        raise _catalog_error(error) from error
    return ProductResponse.model_validate(result)


@router.post(
    "/products/{product_id}/skus",
    response_model=SKUResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_sku(
    product_id: int,
    payload: SKUCreate,
    context: Annotated[TenantContext, Depends(scoped_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SKUResponse:
    if payload.product_id != product_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Product mismatch",
        )
    try:
        result = await _service(session, context).create_sku(
            product_id=product_id,
            sku_code=payload.sku_code,
            sku_name=payload.sku_name,
            variant_attributes=payload.variant_attributes,
            price_minor=payload.price_minor,
            currency=payload.currency,
        )
    except (CatalogNotFound, CatalogConflict) as error:
        raise _catalog_error(error) from error
    except IntegrityError as error:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="SKU code already exists",
        ) from error
    return SKUResponse.model_validate(result)


@router.patch("/skus/{sku_id}", response_model=SKUResponse)
async def update_sku(
    sku_id: int,
    payload: SKUUpdate,
    context: Annotated[TenantContext, Depends(scoped_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SKUResponse:
    try:
        result = await _service(session, context).update_sku(
            sku_id=sku_id,
            sku_name=payload.sku_name,
            variant_attributes=payload.variant_attributes,
            price_minor=payload.price_minor,
            is_active=payload.is_active,
        )
    except (CatalogNotFound, InvalidCatalogState) as error:
        raise _catalog_error(error) from error
    return SKUResponse.model_validate(result)


@router.post("/products/{product_id}/publish", response_model=ProductResponse)
async def publish_product(
    product_id: int,
    context: Annotated[TenantContext, Depends(scoped_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProductResponse:
    try:
        result = await _service(session, context).publish_product(product_id=product_id)
    except (CatalogNotFound, InvalidCatalogState) as error:
        raise _catalog_error(error) from error
    return ProductResponse.model_validate(result)


@router.post("/products/{product_id}/archive", response_model=ProductResponse)
async def archive_product(
    product_id: int,
    context: Annotated[TenantContext, Depends(scoped_tenant_context)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProductResponse:
    try:
        result = await _service(session, context).archive_product(product_id=product_id)
    except CatalogNotFound as error:
        raise _catalog_error(error) from error
    return ProductResponse.model_validate(result)
