from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.core.config import Settings
from app.core.security import (
    InvalidAccessToken,
    create_access_token,
    create_csrf_token,
    create_refresh_token,
    csrf_tokens_match,
    decode_access_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


def test_password_hash_never_equals_plaintext_and_verifies_correct_password() -> None:
    password = "correct horse battery staple"

    password_hash = hash_password(password)

    assert password_hash != password
    assert verify_password(password, password_hash) is True
    assert verify_password("incorrect password", password_hash) is False


def test_access_token_recovers_the_issuing_user_id() -> None:
    settings = Settings(
        _env_file=None,
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
    )

    token = create_access_token(user_id=42, settings=settings)

    assert decode_access_token(token, settings=settings).user_id == 42


def test_access_token_rejects_a_tampered_signature() -> None:
    settings = Settings(
        _env_file=None,
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
    )
    token = create_access_token(user_id=42, settings=settings)

    with pytest.raises(InvalidAccessToken):
        decode_access_token(f"{token}tampered", settings=settings)


def test_access_token_rejects_a_validly_signed_non_access_token() -> None:
    settings = Settings(
        _env_file=None,
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
    )
    now = datetime.now(UTC)
    refresh_like_token = jwt.encode(
        {
            "sub": "42",
            "typ": "refresh",
            "jti": "test-refresh-token-id",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            "iss": settings.auth_jwt_issuer,
        },
        settings.auth_jwt_secret.get_secret_value(),
        algorithm=settings.auth_jwt_algorithm,
    )

    with pytest.raises(InvalidAccessToken):
        decode_access_token(refresh_like_token, settings=settings)


def test_refresh_tokens_are_random_and_only_their_hash_is_stable() -> None:
    first_token = create_refresh_token()
    second_token = create_refresh_token()

    assert first_token != second_token
    assert hash_refresh_token(first_token) == hash_refresh_token(first_token)
    assert hash_refresh_token(first_token) != first_token


def test_csrf_validation_requires_two_matching_values() -> None:
    assert csrf_tokens_match("csrf-cookie", "csrf-cookie") is True
    assert csrf_tokens_match("csrf-cookie", "different-header") is False
    assert csrf_tokens_match("csrf-cookie", None) is False
    assert csrf_tokens_match(None, "csrf-header") is False


def test_csrf_token_is_random_and_can_be_matched_by_the_client_header() -> None:
    first_token = create_csrf_token()
    second_token = create_csrf_token()

    assert first_token != second_token
    assert csrf_tokens_match(first_token, first_token) is True
