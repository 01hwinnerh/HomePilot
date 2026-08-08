import asyncio

import pytest

from app.core.config import Settings
from app.modules.identity.rate_limit import AuthRateLimiter, AuthRateLimitExceeded


class FakeRedis:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, int | None]] = []
        self.value = 0

    async def get(self, key: str) -> str | None:
        return str(self.value) if self.value else None

    async def delete(self, key: str) -> None:
        self.value = 0

    async def incr(self, key: str) -> int:
        self.calls.append(("incr", key, None))
        self.value += 1
        return self.value

    async def expire(self, key: str, seconds: int) -> None:
        self.calls.append(("expire", key, seconds))


def test_rate_limiter_uses_hashed_identity_and_rejects_after_threshold() -> None:
    settings = Settings(
        _env_file=None,
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
        auth_rate_limit_max_attempts=2,
    )
    redis = FakeRedis()
    limiter = AuthRateLimiter(redis=redis, settings=settings)

    asyncio.run(
        limiter.check(
            scope="credentials",
            identity="buyer@example.com",
            client_ip="127.0.0.1",
        )
    )
    asyncio.run(
        limiter.check(
            scope="credentials",
            identity="buyer@example.com",
            client_ip="127.0.0.1",
        )
    )
    with pytest.raises(AuthRateLimitExceeded):
        asyncio.run(
            limiter.check(
                scope="credentials",
                identity="buyer@example.com",
                client_ip="127.0.0.1",
            )
        )

    key = redis.calls[0][1]
    assert "buyer@example.com" not in key
    assert "127.0.0.1" not in key
    assert redis.calls[1] == ("expire", key, settings.auth_rate_limit_window_seconds)


def test_refresh_sessions_on_the_same_ip_use_separate_hashed_limit_buckets() -> None:
    settings = Settings(
        _env_file=None,
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
    )
    redis = FakeRedis()
    limiter = AuthRateLimiter(redis=redis, settings=settings)

    asyncio.run(
        limiter.check(
            scope="refresh",
            identity="hashed-refresh-token-a",
            client_ip="127.0.0.1",
        )
    )
    asyncio.run(
        limiter.check(
            scope="refresh",
            identity="hashed-refresh-token-b",
            client_ip="127.0.0.1",
        )
    )

    first_key = redis.calls[0][1]
    second_key = redis.calls[2][1]
    assert first_key != second_key
    assert "hashed-refresh-token-a" not in first_key
    assert "hashed-refresh-token-b" not in second_key


def test_credential_failure_bucket_can_be_cleared_after_success() -> None:
    settings = Settings(
        _env_file=None,
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
        auth_rate_limit_max_attempts=2,
    )
    redis = FakeRedis()
    limiter = AuthRateLimiter(redis=redis, settings=settings)

    for _ in range(2):
        asyncio.run(
            limiter.record_credential_failure(
                identity="buyer@example.com",
                client_ip="127.0.0.1",
            )
        )

    with pytest.raises(AuthRateLimitExceeded):
        asyncio.run(
            limiter.check_credentials(
                identity="buyer@example.com",
                client_ip="127.0.0.1",
            )
        )

    asyncio.run(
        limiter.clear_credential_failures(
            identity="buyer@example.com",
            client_ip="127.0.0.1",
        )
    )
    asyncio.run(
        limiter.check_credentials(
            identity="buyer@example.com",
            client_ip="127.0.0.1",
        )
    )


def test_request_bucket_limits_by_ip_with_a_separate_threshold() -> None:
    settings = Settings(
        _env_file=None,
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
        auth_request_rate_limit_max_attempts=2,
    )
    redis = FakeRedis()
    limiter = AuthRateLimiter(redis=redis, settings=settings)

    asyncio.run(limiter.check_request(client_ip="127.0.0.1"))
    asyncio.run(limiter.check_request(client_ip="127.0.0.1"))
    with pytest.raises(AuthRateLimitExceeded):
        asyncio.run(limiter.check_request(client_ip="127.0.0.1"))
