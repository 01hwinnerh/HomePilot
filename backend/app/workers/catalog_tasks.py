import asyncio
from typing import Any

from elasticsearch import AsyncElasticsearch

from app.core.config import get_settings
from app.core.database import get_database
from app.modules.catalog.indexer import CatalogEventProcessor, CatalogIndexer
from app.modules.catalog.repositories import PublicCatalogRepository
from app.modules.catalog.search.elasticsearch import ElasticsearchCatalogSearch
from app.shared.outbox.service import OutboxEventStore
from app.workers.celery_app import celery_app


@celery_app.task(name="catalog.project_product")
def project_catalog_product(product_id: int) -> None:
    if product_id <= 0:
        raise ValueError("product_id must be positive")
    asyncio.run(_project_product(product_id=product_id))


async def _project_product(*, product_id: int) -> None:
    settings = get_settings()
    database = get_database()
    client = AsyncElasticsearch(
        settings.elasticsearch_url,
        request_timeout=settings.elasticsearch_request_timeout_seconds,
        max_retries=settings.elasticsearch_max_retries,
        retry_on_timeout=True,
    )
    try:
        async with database.session() as session:
            indexer = CatalogIndexer(
                repository=PublicCatalogRepository(session=session),
                search=ElasticsearchCatalogSearch(
                    client=client,
                    index_alias=settings.elasticsearch_index_alias,
                ),
            )
            await indexer.project_product(product_id=product_id)
    finally:
        await client.close()


@celery_app.task(bind=True, name="catalog.project_event", max_retries=3)
def project_catalog_event(task: Any, event_id: str) -> bool:
    """Consume an outbox event and retry transient projection failures."""

    try:
        return asyncio.run(_project_event(event_id=event_id))
    except Exception as exc:
        retries = int(task.request.retries)
        retry = task.retry
        raise retry(exc=exc, countdown=min(60, 2**retries)) from exc


async def _project_event(*, event_id: str) -> bool:
    settings = get_settings()
    database = get_database()
    client = AsyncElasticsearch(
        settings.elasticsearch_url,
        request_timeout=settings.elasticsearch_request_timeout_seconds,
        max_retries=settings.elasticsearch_max_retries,
        retry_on_timeout=True,
    )
    try:
        async with database.session() as session:
            indexer = CatalogIndexer(
                repository=PublicCatalogRepository(session=session),
                search=ElasticsearchCatalogSearch(
                    client=client,
                    index_alias=settings.elasticsearch_index_alias,
                ),
            )
            processor = CatalogEventProcessor(
                events=OutboxEventStore(session=session),
                indexer=indexer,
            )
            return await processor.process(event_id=event_id)
    finally:
        await client.close()
