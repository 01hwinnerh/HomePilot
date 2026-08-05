from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from hmac import compare_digest
from secrets import token_urlsafe
from uuid import uuid4

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

from app.core.config import Settings

_password_hasher = PasswordHasher()


class InvalidAccessToken(ValueError):
    """Raised when a bearer token is not a valid access token."""


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: int
    token_id: str


def hash_password(password: str) -> str:
    """Return an Argon2 hash for a user password."""

    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Return whether a password matches an Argon2 hash."""

    try:
        return _password_hasher.verify(password_hash, password)
    except VerificationError:
        return False


def create_refresh_token() -> str:
    """Return a high-entropy opaque token for a refresh session."""

    return token_urlsafe(48)


def create_csrf_token() -> str:
    """Return a browser-readable token for double-submit CSRF protection."""

    return token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    """Return the database-safe SHA-256 representation of a refresh token."""

    return sha256(token.encode("utf-8")).hexdigest()


def csrf_tokens_match(cookie_value: str | None, header_value: str | None) -> bool:
    """Return whether a request supplied the matching double-submit CSRF token."""

    return (
        cookie_value is not None
        and header_value is not None
        and compare_digest(cookie_value, header_value)
    )


def create_access_token(*, user_id: int, settings: Settings) -> str:
    """Sign a short-lived bearer token for an authenticated user."""

    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "typ": "access",
        "jti": uuid4().hex,
        "iat": now,
        "exp": now + timedelta(minutes=settings.auth_access_token_minutes),
        "iss": settings.auth_jwt_issuer,
    }
    return jwt.encode(
        payload,
        settings.auth_jwt_secret.get_secret_value(),
        algorithm=settings.auth_jwt_algorithm,
    )


def decode_access_token(token: str, *, settings: Settings) -> AccessTokenClaims:
    """Verify a bearer token and return its trusted user identity."""

    try:
        payload = jwt.decode(
            token,
            settings.auth_jwt_secret.get_secret_value(),
            algorithms=[settings.auth_jwt_algorithm],
            issuer=settings.auth_jwt_issuer,
            options={"require": ["exp", "iat", "iss", "jti", "sub", "typ"]},
        )
        if payload["typ"] != "access":
            raise InvalidAccessToken("Token type is not access.")
        return AccessTokenClaims(user_id=int(payload["sub"]), token_id=payload["jti"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as error:
        if isinstance(error, InvalidAccessToken):
            raise
        raise InvalidAccessToken("Invalid access token.") from error
