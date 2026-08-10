from typing import Protocol

from app.modules.catalog.repositories import PublicProductRecord
from app.modules.catalog.search.contracts import CatalogSearchPort


class PublicCatalogSearchRepository(Protocol):
    async def list_public_product_records_by_ids(
        self,
        *,
        product_ids: list[int],
    ) -> list[PublicProductRecord]: ...


class SearchUnavailable(RuntimeError):
    """Raised when Elasticsearch cannot serve a public search request."""


class CatalogSearchService:
    def __init__(
        self,
        *,
        repository: PublicCatalogSearchRepository,
        search: CatalogSearchPort,
    ) -> None:
        self._repository = repository
        self._search = search

    async def search(
        self,
        *,
        query: str | None,
        category_id: int | None,
        offset: int,
        limit: int,
    ) -> list[PublicProductRecord]:
        try:
            hits = await self._search.search_product_ids(
                query=query,
                category_id=category_id,
                offset=offset,
                limit=limit,
            )
        except Exception as exc:
            raise SearchUnavailable from exc
        product_ids = [hit.product_id for hit in hits]
        return await self._repository.list_public_product_records_by_ids(product_ids=product_ids)
