import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _settings(**overrides: object) -> Settings:
    return Settings(
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
        **overrides,
    )


def test_settings_expose_elasticsearch_connection_contract() -> None:
    settings = _settings(
        elasticsearch_url="http://localhost:9200",
        elasticsearch_index_alias="catalog-products-read",
        elasticsearch_request_timeout_seconds=3,
        elasticsearch_max_retries=2,
    )

    assert settings.elasticsearch_url == "http://localhost:9200"
    assert settings.elasticsearch_index_alias == "catalog-products-read"
    assert settings.elasticsearch_request_timeout_seconds == 3
    assert settings.elasticsearch_max_retries == 2


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("elasticsearch_url", "localhost:9200"),
        ("elasticsearch_url", "ftp://localhost:9200"),
        ("elasticsearch_index_alias", ""),
        ("elasticsearch_index_alias", "catalog products"),
        ("elasticsearch_request_timeout_seconds", 0),
        ("elasticsearch_max_retries", -1),
    ],
)
def test_settings_reject_invalid_elasticsearch_values(field: str, value: object) -> None:
    with pytest.raises(ValidationError):
        _settings(**{field: value})
