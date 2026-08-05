import logging
from typing import Literal

SecurityEventName = Literal[
    "auth.registered",
    "auth.login_succeeded",
    "auth.login_failed",
    "auth.refresh_succeeded",
    "auth.refresh_rejected",
    "auth.logout",
    "auth.user_inactive",
    "tenancy.access_denied",
]

logger = logging.getLogger(__name__)


def record_security_event(
    event: SecurityEventName,
    *,
    result: str,
    user_id: int | None = None,
    session_id: int | None = None,
    request_id: str | None = None,
    failure_reason: str | None = None,
) -> None:
    """Emit a deliberately token-free structured security event."""

    payload = {
        "event": event,
        "result": result,
        "user_id": user_id,
        "session_id": session_id,
        "request_id": request_id,
        "failure_reason": failure_reason,
    }
    logger.info("security_event", extra={"security_event": payload})
