"""Rebuild the catalog search projection from MySQL."""

import asyncio
from datetime import UTC, datetime

from app.core.config import get_settings
from app.core.database import get_database
from app.modules.catalog.repositories import PublicCatalogRepository
from app.modules.catalog.search.elasticsearch import ElasticsearchCatalogSearch


async def rebuild() -> None:
    settings = get_settings()
    database = get_database()
    from elasticsearch import AsyncElasticsearch

    client = AsyncElasticsearch(settings.elasticsearch_url)
    try:
        async with database.session() as session:
            repository = PublicCatalogRepository(session=session)
            search = ElasticsearchCatalogSearch(
                client=client,
                index_alias=settings.elasticsearch_index_alias,
            )
            index_name = "catalog-products-v" + datetime.now(UTC).strftime("%Y%m%d%H%M%S")
            await search.create_versioned_index(index=index_name)
            documents: list[dict[str, object]] = []
            offset = 0
            while True:
                products = await repository.list_published_products(offset=offset, limit=500)
                if not products:
                    break
                for product in products:
                    document = await repository.get_public_product_document(product_id=product.id)
                    if document is not None:
                        documents.append(document)
                offset += len(products)
            await search.bulk_index_products(documents=documents, index=index_name)
            await search.switch_read_alias(index=index_name)
    finally:
        await client.close()
        await database.dispose()


if __name__ == "__main__":
    asyncio.run(rebuild())
