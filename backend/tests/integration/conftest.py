import pytest

from app.core.config import get_settings
from app.core.database import validate_test_database_isolation


@pytest.fixture(scope="session")
def isolated_test_database_url() -> str:
    settings = get_settings()
    validate_test_database_isolation(
        database_url=settings.database_url,
        test_database_url=settings.test_database_url,
    )
    return settings.test_database_url
