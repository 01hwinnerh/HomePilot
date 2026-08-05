import asyncio
import logging

import pytest

from app.core.config import Settings
from app.modules.identity.security_events import record_security_event
from app.modules.identity.service import AuthService, InvalidCredentials


class MissingUserSession:
    async def scalar(self, statement: object) -> None:
        return None


def test_login_security_event_never_contains_submitted_password(
    caplog: pytest.LogCaptureFixture,
) -> None:
    password = "never-log-this-password"
    settings = Settings(
        _env_file=None,
        auth_jwt_secret="test-signing-secret-that-is-never-used-outside-this-test",
    )

    with caplog.at_level(logging.INFO):
        with pytest.raises(InvalidCredentials):
            asyncio.run(
                AuthService(session=MissingUserSession(), settings=settings).login(
                    email="missing@example.com",
                    password=password,
                )
            )

    security_records = [
        record for record in caplog.records if getattr(record, "security_event", None) is not None
    ]
    assert len(security_records) == 1
    assert password not in caplog.text
    assert password not in repr(security_records[0].security_event)


def test_security_event_payload_uses_only_the_allowlisted_fields(
    caplog: pytest.LogCaptureFixture,
) -> None:
    sensitive_values = [
        "access-jwt-secret",
        "refresh-token-secret",
        "csrf-token-secret",
        "Cookie: refresh_token=refresh-token-secret",
        "Authorization: Bearer access-jwt-secret",
    ]

    with caplog.at_level(logging.INFO):
        record_security_event(
            "auth.refresh_rejected",
            result="denied",
            user_id=1,
            session_id=2,
            request_id="request-3",
            failure_reason="expired",
        )

    record = next(record for record in caplog.records if getattr(record, "security_event", None))
    payload = record.security_event
    assert set(payload) == {
        "event",
        "result",
        "user_id",
        "session_id",
        "request_id",
        "failure_reason",
    }
    for value in sensitive_values:
        assert value not in caplog.text
        assert value not in repr(record.__dict__)
