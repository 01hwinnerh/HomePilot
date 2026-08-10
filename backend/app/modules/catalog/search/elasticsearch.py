from elasticsearch import AsyncElasticsearch

from app.modules.catalog.search.contracts import SearchHit
from app.modules.catalog.search.mapping import catalog_product_mapping


class ElasticsearchCatalogSearch:
    def __init__(self, *, client: AsyncElasticsearch, index_alias: str) -> None:
        self._client = client
        self._index_alias = index_alias

    async def search_product_ids(
        self,
        *,
        query: str | None,
        category_id: int | None,
        offset: int,
        limit: int,
    ) -> list[SearchHit]:
        filters: list[dict[str, object]] = []
        if category_id is not None:
            filters.append({"term": {"category_id": str(category_id)}})
        must = (
            [
                {
                    "multi_match": {
                        "query": query,
                        "fields": ["name^3", "description", "merchant_name", "store_name"],
                    }
                }
            ]
            if query
            else [{"match_all": {}}]
        )
        response = await self._client.search(
            index=self._index_alias,
            from_=offset,
            size=limit,
            query={"bool": {"must": must, "filter": filters}},
        )
        return [
            SearchHit(product_id=int(hit["_source"]["product_id"]), score=float(hit["_score"] or 0))
            for hit in response["hits"]["hits"]
        ]

    async def index_product(
        self,
        document: dict[str, object],
        *,
        index: str | None = None,
    ) -> None:
        await self._client.index(
            index=index or self._index_alias,
            id=str(document["product_id"]),
            document=document,
            refresh=False,
        )

    async def delete_product(self, *, product_id: int, index: str | None = None) -> None:
        await self._client.delete(
            index=index or self._index_alias,
            id=str(product_id),
            ignore=[404],
            refresh=False,
        )

    async def create_versioned_index(self, *, index: str) -> None:
        exists = await self._client.indices.exists(index=index)
        if not exists:
            await self._client.indices.create(index=index, **catalog_product_mapping())

    async def switch_read_alias(self, *, index: str) -> None:
        current = await self._client.indices.get_alias(name=self._index_alias, ignore=[404])
        if "error" in current:
            current = {}
        actions: list[dict[str, object]] = [
            {"remove": {"index": existing, "alias": self._index_alias}}
            for existing in current
        ]
        actions.append({"add": {"index": index, "alias": self._index_alias}})
        await self._client.indices.update_aliases(actions=actions)

    async def bulk_index_products(
        self,
        *,
        documents: list[dict[str, object]],
        index: str,
    ) -> None:
        if not documents:
            return
        operations: list[dict[str, object]] = []
        for document in documents:
            operations.extend(
                [
                    {"index": {"_index": index, "_id": str(document["product_id"])}},
                    document,
                ]
            )
        response = await self._client.bulk(operations=operations, refresh=False)
        if response.get("errors"):
            raise RuntimeError("Elasticsearch bulk indexing failed")
