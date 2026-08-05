from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.shared.models.utc_datetime import UTCDateTime


def test_utc_datetime_normalizes_and_restores_aware_values() -> None:
    value = datetime(2026, 8, 5, 20, tzinfo=timezone(timedelta(hours=8)))
    value_type = UTCDateTime()

    stored = value_type.process_bind_param(value, dialect=None)
    restored = value_type.process_result_value(stored, dialect=None)

    assert stored == datetime(2026, 8, 5, 12)
    assert restored == datetime(2026, 8, 5, 12, tzinfo=UTC)


def test_utc_datetime_rejects_naive_values() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        UTCDateTime().process_bind_param(datetime(2026, 8, 5, 12), dialect=None)
