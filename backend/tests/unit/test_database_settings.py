import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_exposes_development_and_test_database_urls() -> None:
    settings = Settings(
        _env_file=None,
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
        database_url="mysql+asyncmy://app:secret@localhost/homepilot",
        test_database_url="mysql+asyncmy://app:secret@localhost/homepilot_test",
    )

    assert settings.database_url.endswith("/homepilot")
    assert settings.test_database_url.endswith("/homepilot_test")


def test_auth_settings_parse_exact_cors_origins_and_keep_safe_defaults() -> None:
    settings = Settings(
        _env_file=None,
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
        backend_cors_origins="http://localhost:5173, http://localhost:5174,",
    )

    assert settings.auth_access_token_minutes == 15
    assert settings.auth_cookie_secure is False
    assert settings.backend_cors_origins == [
        "http://localhost:5173",
        "http://localhost:5174",
    ]


def test_auth_settings_default_refresh_session_lifetime_is_seven_days() -> None:
    settings = Settings(
        _env_file=None,
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
    )

    assert settings.auth_refresh_token_days == 7


def test_auth_settings_default_cookie_policy_is_lax() -> None:
    settings = Settings(
        _env_file=None,
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
    )

    assert settings.auth_cookie_same_site == "lax"


def test_auth_settings_default_rate_limit_protects_credential_endpoints() -> None:
    settings = Settings(
        _env_file=None,
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
    )

    assert settings.auth_rate_limit_enabled is True
    assert settings.auth_rate_limit_max_attempts == 5
    assert settings.auth_rate_limit_window_seconds == 900


def test_settings_expose_redis_url_for_auth_rate_limiting() -> None:
    settings = Settings(
        _env_file=None,
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
        redis_url="redis://localhost:6379/15",
    )

    assert settings.redis_url == "redis://localhost:6379/15"


def test_auth_settings_reject_wildcard_cors_when_credentials_are_used() -> None:
    with pytest.raises(ValidationError, match="must not contain '\\*'"):
        Settings(
            _env_file=None,
            auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
            backend_cors_origins="*",
        )


@pytest.mark.parametrize(
    ("field_name", "value"),
    [("auth_access_token_minutes", 0), ("auth_refresh_token_days", 0)],
)
def test_auth_settings_reject_non_positive_session_durations(
    field_name: str,
    value: int,
) -> None:
    with pytest.raises(ValidationError):
        Settings(
            _env_file=None,
            auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
            **{field_name: value},
        )
