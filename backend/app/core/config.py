from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    """从本地 .env 读取的集中式配置。

    业务代码只依赖此对象，不直接读取环境变量。
    """

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "HomePilot API"
    app_env: str = "development"
    app_debug: bool = False
    api_v1_prefix: str = "/api/v1"
    backend_cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://localhost:5174",
    ]
    database_url: str = (
        "mysql+asyncmy://homepilot:change-me-local@127.0.0.1:3306/homepilot"
    )
    test_database_url: str = (
        "mysql+asyncmy://homepilot:change-me-local@127.0.0.1:3306/homepilot_test"
    )
    redis_url: str = "redis://127.0.0.1:6379/0"
    elasticsearch_url: str = "http://127.0.0.1:9200"
    elasticsearch_index_alias: str = Field(
        default="catalog-products-read",
        min_length=1,
        max_length=255,
        pattern=r"^[a-z0-9][a-z0-9._-]*$",
    )
    elasticsearch_request_timeout_seconds: float = Field(default=2, gt=0, le=30)
    elasticsearch_max_retries: int = Field(default=3, ge=0, le=5)
    auth_jwt_secret: SecretStr
    auth_jwt_issuer: str = "homepilot-api"
    auth_jwt_algorithm: Literal["HS256"] = "HS256"
    auth_access_token_minutes: int = Field(default=15, ge=1, le=60)
    auth_refresh_token_days: int = Field(default=7, ge=1, le=30)
    auth_cookie_secure: bool = False
    auth_cookie_same_site: Literal["lax"] = "lax"
    auth_refresh_cookie_name: str = "refresh_token"
    auth_csrf_cookie_name: str = "csrf_token"
    auth_cookie_path: str = "/api/v1/auth"
    auth_csrf_cookie_path: str = "/"
    auth_rate_limit_enabled: bool = True
    auth_rate_limit_max_attempts: int = Field(default=5, ge=1, le=100)
    auth_rate_limit_window_seconds: int = Field(default=900, ge=1, le=3600)
    auth_request_rate_limit_max_attempts: int = Field(default=120, ge=1, le=1000)
    auth_request_rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    demo_seed_password: SecretStr | None = None

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        else:
            origins = value
        if "*" in origins:
            raise ValueError("BACKEND_CORS_ORIGINS must not contain '*'.")
        return origins

    @field_validator("elasticsearch_url")
    @classmethod
    def validate_elasticsearch_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("ELASTICSEARCH_URL must be an absolute HTTP(S) URL.")
        return value.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    """在一个进程内复用配置实例。"""

    return Settings()
