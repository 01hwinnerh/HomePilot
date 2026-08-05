import pytest

from app.core.database import Database


def test_database_engine_enables_pre_ping() -> None:
    database = Database("mysql+asyncmy://app:secret@localhost/homepilot")

    assert database.engine.pool._pre_ping is True


@pytest.mark.asyncio
async def test_database_session_does_not_expire_on_commit() -> None:
    database = Database("mysql+asyncmy://app:secret@localhost/homepilot")

    async with database.session() as session:
        assert session.sync_session.expire_on_commit is False

    await database.dispose()
