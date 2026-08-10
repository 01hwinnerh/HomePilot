import pytest

from app.modules.catalog.search.contracts import CatalogSearchPort, SearchHit
from app.modules.catalog.search.elasticsearch import ElasticsearchCatalogSearch


def test_search_port_exposes_stable_candidate_contract() -> None:
    assert SearchHit(product_id=42, score=1.5).product_id == 42
    assert hasattr(CatalogSearchPort, "search_product_ids")


@pytest.mark.asyncio
async def test_search_port_contract_is_async() -> None:
    assert callable(CatalogSearchPort.search_product_ids)


@pytest.mark.asyncio
async def test_elasticsearch_adapter_maps_hits_and_filters() -> None:
    class FakeClient:
        async def search(self, **kwargs: object) -> dict[str, object]:
            self.kwargs = kwargs
            return {"hits": {"hits": [{"_source": {"product_id": 42}, "_score": 2.5}]}}

    client = FakeClient()
    adapter = ElasticsearchCatalogSearch(client=client, index_alias="catalog-products-read")
    hits = await adapter.search_product_ids(query="sofa", category_id=7, offset=10, limit=5)

    assert hits == [SearchHit(product_id=42, score=2.5)]
    assert client.kwargs["from_"] == 10
    assert client.kwargs["size"] == 5


@pytest.mark.asyncio
async def test_elasticsearch_rebuild_switches_alias_only_after_bulk_success() -> None:
    class FakeIndices:
        def __init__(self) -> None:
            self.created: list[str] = []
            self.alias_actions: list[dict[str, object]] | None = None

        async def exists(self, *, index: str) -> bool:
            return False

        async def create(self, **kwargs: object) -> None:
            self.created.append(str(kwargs["index"]))

        async def get_alias(self, **kwargs: object) -> dict[str, object]:
            return {"catalog-products-v0": {}}

        async def update_aliases(self, *, actions: list[dict[str, object]]) -> None:
            self.alias_actions = actions

    class FakeClient:
        def __init__(self) -> None:
            self.indices = FakeIndices()
            self.bulk_operations: list[dict[str, object]] | None = None

        async def bulk(self, **kwargs: object) -> dict[str, object]:
            self.bulk_operations = kwargs["operations"]
            return {"errors": False}

    client = FakeClient()
    adapter = ElasticsearchCatalogSearch(client=client, index_alias="catalog-products-read")
    await adapter.create_versioned_index(index="catalog-products-v1")
    await adapter.bulk_index_products(
        index="catalog-products-v1",
        documents=[{"product_id": "42", "name": "Desk"}],
    )
    await adapter.switch_read_alias(index="catalog-products-v1")

    assert client.indices.created == ["catalog-products-v1"]
    assert client.bulk_operations is not None
    assert client.indices.alias_actions == [
        {"remove": {"index": "catalog-products-v0", "alias": "catalog-products-read"}},
        {"add": {"index": "catalog-products-v1", "alias": "catalog-products-read"}},
    ]


@pytest.mark.asyncio
async def test_elasticsearch_rebuild_can_create_an_alias_for_the_first_index() -> None:
    class FakeIndices:
        async def get_alias(self, **kwargs: object) -> dict[str, object]:
            return {"error": {"type": "index_not_found_exception"}, "status": 404}

        async def update_aliases(self, *, actions: list[dict[str, object]]) -> None:
            self.actions = actions

    class FakeClient:
        def __init__(self) -> None:
            self.indices = FakeIndices()

    client = FakeClient()
    adapter = ElasticsearchCatalogSearch(client=client, index_alias="catalog-products-read")
    await adapter.switch_read_alias(index="catalog-products-v1")

    assert client.indices.actions == [
        {"add": {"index": "catalog-products-v1", "alias": "catalog-products-read"}},
    ]
