import pytest

from app.modules.catalog.indexer import CatalogIndexer


@pytest.mark.asyncio
async def test_indexer_deletes_non_public_product() -> None:
    class FakeSearch:
        async def delete_product(self, *, product_id: int) -> None:
            self.deleted = product_id

    class FakeRepository:
        async def get_public_product_document(self, *, product_id: int) -> dict[str, object] | None:
            return None

    search = FakeSearch()
    await CatalogIndexer(repository=FakeRepository(), search=search).project_product(product_id=7)

    assert search.deleted == 7


@pytest.mark.asyncio
async def test_indexer_indexes_current_public_document() -> None:
    class FakeSearch:
        def __init__(self) -> None:
            self.indexed: dict[str, object] | None = None

        async def index_product(self, document: dict[str, object]) -> None:
            self.indexed = document

    document = {
        "product_id": "7",
        "merchant_id": "2",
        "store_id": "3",
        "name": "Walnut Table",
        "active_skus": [{"sku_id": "9", "price_minor": 199900}],
    }

    class FakeRepository:
        async def get_public_product_document(self, *, product_id: int) -> dict[str, object] | None:
            assert product_id == 7
            return document

    search = FakeSearch()
    await CatalogIndexer(repository=FakeRepository(), search=search).project_product(product_id=7)

    assert search.indexed == document


@pytest.mark.asyncio
async def test_event_processor_is_idempotent_and_projects_current_state() -> None:
    from app.modules.catalog.indexer import CatalogEventProcessor

    class FakeEvent:
        aggregate_type = "product"
        aggregate_id = 7

    class FakeEvents:
        def __init__(self) -> None:
            self.claims = 0
            self.published = 0
            self.failed = 0

        async def claim(self, *, event_id: str) -> FakeEvent | None:
            self.claims += 1
            return FakeEvent() if self.claims == 1 else None

        async def mark_published(self, *, event_id: str) -> None:
            self.published += 1

        async def mark_failed(self, *, event_id: str, error: str) -> None:
            self.failed += 1

        async def product_ids_for_event(self, event: FakeEvent) -> list[int]:
            return [event.aggregate_id]

    class FakeIndexer:
        def __init__(self) -> None:
            self.projected: list[int] = []

        async def project_product(self, *, product_id: int) -> None:
            self.projected.append(product_id)

    events = FakeEvents()
    indexer = FakeIndexer()
    processor = CatalogEventProcessor(events=events, indexer=indexer)

    assert await processor.process(event_id="event-1") is True
    assert await processor.process(event_id="event-1") is False
    assert indexer.projected == [7]
    assert events.published == 1
    assert events.failed == 0


@pytest.mark.asyncio
async def test_event_processor_records_safe_failure_summary() -> None:
    from app.modules.catalog.indexer import CatalogEventProcessor

    class FakeEvent:
        aggregate_type = "product"
        aggregate_id = 7

    class FakeEvents:
        def __init__(self) -> None:
            self.error: str | None = None

        async def claim(self, *, event_id: str) -> FakeEvent:
            return FakeEvent()

        async def product_ids_for_event(self, event: FakeEvent) -> list[int]:
            return [event.aggregate_id]

        async def mark_published(self, *, event_id: str) -> None:
            raise AssertionError("failed projection must not be published")

        async def mark_failed(self, *, event_id: str, error: str) -> None:
            self.error = error

    class FailingIndexer:
        async def project_product(self, *, product_id: int) -> None:
            raise ConnectionError("provider secret should not be logged")

    events = FakeEvents()
    processor = CatalogEventProcessor(events=events, indexer=FailingIndexer())

    with pytest.raises(ConnectionError):
        await processor.process(event_id="event-1")

    assert events.error == "ConnectionError"
