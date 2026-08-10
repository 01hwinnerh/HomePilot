import pytest

from app.modules.catalog.search.contracts import SearchHit
from app.modules.catalog.search.service import CatalogSearchService, SearchUnavailable


@pytest.mark.asyncio
async def test_search_service_rechecks_mysql_and_preserves_es_order() -> None:
    class FakeSearch:
        async def search_product_ids(
            self, *, query: str | None, category_id: int | None, offset: int, limit: int
        ) -> list[SearchHit]:
            return [SearchHit(product_id=2, score=2), SearchHit(product_id=1, score=1)]

    class FakeRepository:
        async def list_public_product_records_by_ids(
            self,
            *,
            product_ids: list[int],
        ) -> list[object]:
            assert product_ids == [2, 1]
            return ["product-2"]

    service = CatalogSearchService(repository=FakeRepository(), search=FakeSearch())
    result = await service.search(query="sofa", category_id=None, offset=0, limit=20)

    assert result == ["product-2"]


@pytest.mark.asyncio
async def test_search_service_maps_provider_failures_to_unavailable() -> None:
    class BrokenSearch:
        async def search_product_ids(self, **kwargs: object) -> list[SearchHit]:
            raise TimeoutError("connection timed out")

    class FakeRepository:
        async def list_public_product_records_by_ids(
            self,
            *,
            product_ids: list[int],
        ) -> list[object]:
            raise AssertionError("MySQL must not be queried after search failure")

    service = CatalogSearchService(repository=FakeRepository(), search=BrokenSearch())

    with pytest.raises(SearchUnavailable):
        await service.search(query=None, category_id=None, offset=0, limit=20)
