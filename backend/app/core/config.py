from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """从本地 .env 读取的集中式配置。

    业务代码只依赖此对象，不直接读取环境变量。
    """

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "HomePilot API"
    app_env: str = "development"
    app_debug: bool = False
    api_v1_prefix: str = "/api/v1"


@lru_cache
def get_settings() -> Settings:
    """在一个进程内复用配置实例。"""

    return Settings()
