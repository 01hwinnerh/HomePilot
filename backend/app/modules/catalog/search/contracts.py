from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SearchHit:
    product_id: int
    score: float


class CatalogSearchPort(Protocol):
    async def search_product_ids(
        self,
        *,
        query: str | None,
        category_id: int | None,
        offset: int,
        limit: int,
    ) -> list[SearchHit]: ...

    async def index_product(self, document: dict[str, object]) -> None: ...

    async def delete_product(self, *, product_id: int) -> None: ...
