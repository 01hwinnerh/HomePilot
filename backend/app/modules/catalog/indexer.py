from typing import Protocol

from app.modules.catalog.search.contracts import CatalogSearchPort


class PublicCatalogDocumentRepository(Protocol):
    async def get_public_product_document(
        self,
        *,
        product_id: int,
    ) -> dict[str, object] | None: ...


class CatalogEventStore(Protocol):
    async def claim(self, *, event_id: str) -> object | None: ...

    async def mark_published(self, *, event_id: str) -> None: ...

    async def mark_failed(self, *, event_id: str, error: str) -> None: ...

    async def product_ids_for_event(self, event: object) -> list[int]: ...


class CatalogIndexer:
    def __init__(
        self,
        *,
        repository: PublicCatalogDocumentRepository,
        search: CatalogSearchPort,
    ) -> None:
        self._repository = repository
        self._search = search

    async def project_product(self, *, product_id: int) -> None:
        document = await self._repository.get_public_product_document(product_id=product_id)
        if document is None:
            await self._search.delete_product(product_id=product_id)
        else:
            await self._search.index_product(document)


class CatalogEventProcessor:
    """Project one durable catalog event using the current MySQL state."""

    def __init__(self, *, events: CatalogEventStore, indexer: CatalogIndexer) -> None:
        self._events = events
        self._indexer = indexer

    async def process(self, *, event_id: str) -> bool:
        event = await self._events.claim(event_id=event_id)
        if event is None:
            return False
        try:
            for product_id in await self._events.product_ids_for_event(event):
                await self._indexer.project_product(product_id=product_id)
        except Exception as exc:
            summary = type(exc).__name__
            await self._events.mark_failed(event_id=event_id, error=summary)
            raise
        await self._events.mark_published(event_id=event_id)
        return True
