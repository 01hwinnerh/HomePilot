from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings
from app.core.database import validate_test_database_isolation

BACKEND_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def isolated_test_database_url() -> str:
    settings = get_settings()
    validate_test_database_isolation(
        database_url=settings.database_url,
        test_database_url=settings.test_database_url,
    )
    return settings.test_database_url


@pytest.fixture
def migrated_identity_database_url(
    isolated_test_database_url: str,
) -> Iterator[str]:
    """Provide a clean migration head for API integration tests."""

    alembic_config = Config(BACKEND_ROOT / "alembic.ini")
    alembic_config.set_main_option("sqlalchemy.url", isolated_test_database_url)
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")
    try:
        yield isolated_test_database_url
    finally:
        command.downgrade(alembic_config, "base")
