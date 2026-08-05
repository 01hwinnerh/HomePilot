import asyncio
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import command

BACKEND_ROOT = Path(__file__).resolve().parents[2]


async def read_database_revision(database_url: str) -> str:
    engine = create_async_engine(database_url)

    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT version_num FROM alembic_version"))
            return result.scalar_one()
    finally:
        await engine.dispose()


def test_alembic_upgrade_reaches_head_on_test_database(
    isolated_test_database_url: str,
) -> None:
    alembic_config = Config(BACKEND_ROOT / "alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", isolated_test_database_url)

    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")

    expected_revision = ScriptDirectory.from_config(alembic_config).get_current_head()
    actual_revision = asyncio.run(read_database_revision(isolated_test_database_url))
    assert actual_revision == expected_revision
