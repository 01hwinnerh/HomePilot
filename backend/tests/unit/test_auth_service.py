import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import Settings
from app.core.security import hash_password, hash_refresh_token
from app.modules.identity.models import AuthSession, User
from app.modules.identity.service import (
    AuthService,
    DuplicateEmail,
    InvalidCredentials,
    InvalidRefreshSession,
)


class RecordingSession:
    def __init__(self) -> None:
        self.added: list[object] = []
        self.committed = False
        self.rolled_back = False
        self.scalar_values: list[object | None] = []
        self.user: User | None = None

    async def scalar(self, statement: object) -> object | None:
        return self.scalar_values.pop(0) if self.scalar_values else None

    async def get(self, model: type[object], ident: int) -> User | None:
        return self.user

    def add(self, instance: object) -> None:
        self.added.append(instance)

    async def flush(self) -> None:
        for instance in self.added:
            if getattr(instance, "id", None) is None:
                instance.id = len(self.added)

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        self.rolled_back = True


def test_register_normalizes_email_and_creates_a_hashed_password() -> None:
    session = RecordingSession()
    settings = Settings(
        _env_file=None,
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
    )

    result = asyncio.run(
        AuthService(session=session, settings=settings).register(
            email=" Buyer@Example.COM ",
            password="safe-password-123",
        )
    )

    assert result.user.email == "buyer@example.com"
    assert result.user.password_hash != "safe-password-123"
    assert result.refresh_token
    assert result.csrf_token
    assert session.committed is True


def test_register_rejects_a_normalized_duplicate_email() -> None:
    session = RecordingSession()
    session.scalar_values = [User(id=1, email="buyer@example.com", password_hash="hash")]
    settings = Settings(
        _env_file=None,
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
    )

    with pytest.raises(DuplicateEmail):
        asyncio.run(
            AuthService(session=session, settings=settings).register(
                email=" BUYER@example.com ",
                password="safe-password-123",
            )
        )


def test_login_uses_the_same_error_for_unknown_and_wrong_credentials() -> None:
    settings = Settings(
        _env_file=None,
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
    )
    missing_session = RecordingSession()
    known_session = RecordingSession()
    known_session.scalar_values = [
        User(
            id=1,
            email="buyer@example.com",
            password_hash=hash_password("correct-password-123"),
        )
    ]

    with pytest.raises(InvalidCredentials) as missing:
        asyncio.run(
            AuthService(session=missing_session, settings=settings).login(
                email="missing@example.com",
                password="wrong-password",
            )
        )
    with pytest.raises(InvalidCredentials) as incorrect:
        asyncio.run(
            AuthService(session=known_session, settings=settings).login(
                email="buyer@example.com",
                password="wrong-password",
            )
        )

    assert str(missing.value) == str(incorrect.value) == "Invalid credentials"


def test_refresh_rotates_an_active_session_once() -> None:
    now = datetime(2026, 8, 5, 12, tzinfo=UTC)
    old_session = AuthSession(
        id=99,
        user_id=1,
        refresh_token_hash=hash_refresh_token("old-token"),
        expires_at=now + timedelta(days=1),
    )
    user = User(id=1, email="buyer@example.com", password_hash="hash", is_active=True)
    session = RecordingSession()
    session.scalar_values = [old_session]
    session.user = user
    settings = Settings(
        _env_file=None,
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
    )

    result = asyncio.run(
        AuthService(session=session, settings=settings).refresh(
            refresh_token="old-token",
            now=now,
        )
    )

    assert old_session.revoked_at == now
    assert old_session.revoked_reason == "rotated"
    assert old_session.replaced_by_session_id == result.session.id
    assert result.refresh_token != "old-token"
    assert session.committed is True


def test_rejected_refresh_releases_its_locked_transaction() -> None:
    now = datetime(2026, 8, 5, 12, tzinfo=UTC)
    revoked_session = AuthSession(
        id=99,
        user_id=1,
        refresh_token_hash=hash_refresh_token("revoked-token"),
        expires_at=now + timedelta(days=1),
        revoked_at=now,
        revoked_reason="rotated",
    )
    session = RecordingSession()
    session.scalar_values = [revoked_session]
    settings = Settings(
        _env_file=None,
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
    )

    with pytest.raises(InvalidRefreshSession):
        asyncio.run(
            AuthService(session=session, settings=settings).refresh(
                refresh_token="revoked-token",
                now=now,
            )
        )

    assert session.rolled_back is True
