from hashlib import sha256
from typing import Literal

from app.core.config import Settings


class AuthRateLimitExceeded(ValueError):
    """Raised when a credential endpoint exceeds its configured fixed window."""

    def __init__(self, message: str, *, retry_after_seconds: int) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


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

        key = self._key(scope=scope, identity=identity, client_ip=client_ip)
        attempts = await self._redis.incr(key)
        if attempts == 1:
            await self._redis.expire(key, self._settings.auth_rate_limit_window_seconds)
        if attempts > self._settings.auth_rate_limit_max_attempts:
            raise AuthRateLimitExceeded(
                "Too many authentication attempts",
                retry_after_seconds=self._settings.auth_rate_limit_window_seconds,
            )

    async def check_request(self, *, client_ip: str) -> None:
        """Apply a broad per-IP request budget independently of credentials."""

        if not self._settings.auth_rate_limit_enabled:
            return

        key = self._key(scope="requests", identity="", client_ip=client_ip)
        attempts = await self._redis.incr(key)
        if attempts == 1:
            await self._redis.expire(key, self._settings.auth_request_rate_limit_window_seconds)
        if attempts > self._settings.auth_request_rate_limit_max_attempts:
            raise AuthRateLimitExceeded(
                "Too many authentication attempts",
                retry_after_seconds=self._settings.auth_request_rate_limit_window_seconds,
            )

    async def check_credentials(self, *, identity: str, client_ip: str) -> None:
        """Reject credentials only after the failure bucket reaches its threshold."""

        if not self._settings.auth_rate_limit_enabled:
            return

        key = self._key(scope="credential-failures", identity=identity, client_ip=client_ip)
        attempts = await self._redis.get(key)
        if attempts is not None and int(attempts) >= self._settings.auth_rate_limit_max_attempts:
            raise AuthRateLimitExceeded(
                "Too many authentication attempts",
                retry_after_seconds=self._settings.auth_rate_limit_window_seconds,
            )

    async def record_credential_failure(self, *, identity: str, client_ip: str) -> None:
        """Count a failed password attempt without counting successful logins."""

        if not self._settings.auth_rate_limit_enabled:
            return

        key = self._key(scope="credential-failures", identity=identity, client_ip=client_ip)
        attempts = await self._redis.incr(key)
        if attempts == 1:
            await self._redis.expire(key, self._settings.auth_rate_limit_window_seconds)

    async def clear_credential_failures(self, *, identity: str, client_ip: str) -> None:
        """Clear failed credential attempts after successful authentication."""

        if self._settings.auth_rate_limit_enabled:
            await self._redis.delete(
                self._key(scope="credential-failures", identity=identity, client_ip=client_ip)
            )

    @staticmethod
    def _key(*, scope: str, identity: str, client_ip: str) -> str:
        key_material = f"{scope}|{identity.strip().casefold()}|{client_ip}"
        identity_hash = sha256(key_material.encode("utf-8")).hexdigest()
        return f"homepilot:auth-rate-limit:{scope}:{identity_hash}"
