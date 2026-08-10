from app.shared.outbox.models import OutboxEvent


def test_outbox_event_has_idempotent_aggregate_and_delivery_fields() -> None:
    columns = {column.name for column in OutboxEvent.__table__.c}

    assert {
        "id",
        "event_type",
        "aggregate_type",
        "aggregate_id",
        "payload",
        "occurred_at",
        "published_at",
        "attempts",
        "last_error",
    } <= columns
