from datetime import UTC, datetime

from fastapi import Response

from app.api.v1.auth import _set_auth_cookies
from app.core.config import Settings
from app.modules.identity.models import AuthSession, User
from app.modules.identity.service import AuthResult


def test_auth_cookies_respect_the_configured_secure_setting() -> None:
    settings = Settings(
        _env_file=None,
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
        auth_cookie_secure=True,
    )
    result = AuthResult(
        user=User(id=1, email="buyer@example.com", password_hash="hash"),
        session=AuthSession(
            id=1,
            user_id=1,
            refresh_token_hash="a" * 64,
            expires_at=datetime.now(UTC),
        ),
        access_token="access-token",
        refresh_token="refresh-token",
        csrf_token="csrf-token",
    )
    response = Response()

    _set_auth_cookies(response=response, result=result, settings=settings)

    refresh_cookie, csrf_cookie = response.headers.getlist("set-cookie")
    assert "Secure" in refresh_cookie
    assert "HttpOnly" in refresh_cookie
    assert "Secure" in csrf_cookie
    assert "HttpOnly" not in csrf_cookie
