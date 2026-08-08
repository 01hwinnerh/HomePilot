import pytest

from app.core.config import Settings
from app.modules.identity.demo_seed import MissingDemoSeedPassword, require_demo_seed_password


def test_demo_seed_password_must_be_explicitly_configured() -> None:
    settings = Settings(
        _env_file=None,
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
    )

    with pytest.raises(MissingDemoSeedPassword, match="DEMO_SEED_PASSWORD") as error:
        require_demo_seed_password(settings)

    assert "test-signing-secret" not in str(error.value)


def test_demo_seed_password_is_extracted_without_logging_it() -> None:
    settings = Settings(
        _env_file=None,
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
        demo_seed_password="safe-demo-password-123",
    )

    assert require_demo_seed_password(settings) == "safe-demo-password-123"


def test_demo_seed_password_must_not_be_blank() -> None:
    settings = Settings(
        _env_file=None,
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
        demo_seed_password="",
    )

    with pytest.raises(MissingDemoSeedPassword, match="DEMO_SEED_PASSWORD"):
        require_demo_seed_password(settings)
