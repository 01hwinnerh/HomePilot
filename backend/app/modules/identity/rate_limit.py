from hashlib import sha256
from typing import Literal

from app.core.config import Settings


class AuthRateLimitExceeded(ValueError):
    """Raised when a credential endpoint exceeds its configured fixed window."""


class AuthRateLimiter:
    """Redis-backed, privacy-preserving fixed-window credential limiter."""

    def __init__(self, *, redis: object, settings: Settings) -> None:
        self._redis = redis
        self._settings = settings

    async def check(
        self,
        *,
        scope: Literal["credentials", "refresh"],
        identity: str,
        client_ip: str,
    ) -> None:
        if not self._settings.auth_rate_limit_enabled:
            return

        key_material = f"{scope}|{identity.strip().casefold()}|{client_ip}"
        identity_hash = sha256(key_material.encode("utf-8")).hexdigest()
        key = f"homepilot:auth-rate-limit:{scope}:{identity_hash}"
        attempts = await self._redis.incr(key)
        if attempts == 1:
            await self._redis.expire(key, self._settings.auth_rate_limit_window_seconds)
        if attempts > self._settings.auth_rate_limit_max_attempts:
            raise AuthRateLimitExceeded("Too many authentication attempts")
