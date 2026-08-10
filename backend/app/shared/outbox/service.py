from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import Product
from app.shared.outbox.models import OutboxEvent


def append_event(
    session: AsyncSession,
    *,
    event_type: str,
    aggregate_type: str,
    aggregate_id: int,
    payload: dict[str, object],
) -> OutboxEvent:
    event = OutboxEvent(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=aggregate_id,
        payload=payload,
    )
    session.add(event)
    return event


class OutboxEventStore:
    """Claim and complete outbox events without trusting their payload."""

    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session

    async def claim(self, *, event_id: str) -> OutboxEvent | None:
        event = await self._session.scalar(
            select(OutboxEvent)
            .where(OutboxEvent.id == event_id)
            .with_for_update()
        )
        if event is None or event.published_at is not None:
            return None
        event.attempts += 1
        await self._session.commit()
        return event

    async def mark_published(self, *, event_id: str) -> None:
        event = await self._session.scalar(select(OutboxEvent).where(OutboxEvent.id == event_id))
        if event is None:
            return
        event.published_at = datetime.now(UTC)
        event.last_error = None
        await self._session.commit()

    async def mark_failed(self, *, event_id: str, error: str) -> None:
        event = await self._session.scalar(select(OutboxEvent).where(OutboxEvent.id == event_id))
        if event is None:
            return
        event.last_error = error[:500]
        await self._session.commit()

    async def product_ids_for_event(self, event: OutboxEvent) -> list[int]:
        if event.aggregate_type in {"product", "sku"}:
            return [event.aggregate_id]
        if event.aggregate_type == "store":
            result = await self._session.scalars(
                select(Product.id).where(Product.store_id == event.aggregate_id)
            )
            return list(result.all())
        return []
