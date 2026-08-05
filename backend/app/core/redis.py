from functools import lru_cache

from redis.asyncio import Redis, from_url

from app.core.config import get_settings


@lru_cache
def get_redis() -> Redis:
    """Return the process-wide async Redis client used by optional infrastructure."""

    settings = get_settings()
    return from_url(settings.redis_url, decode_responses=True)


async def close_redis() -> None:
    """Close the cached Redis connection pool during application shutdown."""

    cached_client = get_redis()
    await cached_client.aclose()
    get_redis.cache_clear()
