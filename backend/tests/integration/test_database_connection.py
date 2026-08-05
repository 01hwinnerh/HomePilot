import pytest
from sqlalchemy import text

from app.core.database import Database


@pytest.mark.asyncio
async def test_test_database_accepts_queries(isolated_test_database_url: str) -> None:
    database = Database(isolated_test_database_url)

    try:
        async with database.session() as session:
            result = await session.execute(text("SELECT 1"))

        assert result.scalar_one() == 1
    finally:
        await database.dispose()


@pytest.mark.asyncio
async def test_database_session_rolls_back_on_error(
    isolated_test_database_url: str,
) -> None:
    database = Database(isolated_test_database_url)

    try:
        async with database.engine.begin() as connection:
            await connection.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS database_transaction_probe "
                    "(id INT PRIMARY KEY) ENGINE=InnoDB"
                )
            )
            await connection.execute(text("DELETE FROM database_transaction_probe"))

        with pytest.raises(RuntimeError, match="force rollback"):
            async with database.session() as session:
                await session.execute(
                    text("INSERT INTO database_transaction_probe (id) VALUES (1)")
                )
                raise RuntimeError("force rollback")

        async with database.session() as session:
            result = await session.execute(
                text("SELECT COUNT(*) FROM database_transaction_probe")
            )

        assert result.scalar_one() == 0
    finally:
        async with database.engine.begin() as connection:
            await connection.execute(text("DROP TABLE IF EXISTS database_transaction_probe"))
        await database.dispose()
