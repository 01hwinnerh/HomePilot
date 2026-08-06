from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db_session
from app.core.security import InvalidAccessToken, decode_access_token
from app.modules.identity.models import User
from app.modules.identity.security_events import record_security_event
from app.shared.tenancy.context import (
    Principal,
    TenantAccessDenied,
    TenantContext,
    TenantContextFactory,
    _issue_principal,
)
from app.shared.tenancy.session import tenant_scope

bearer_scheme = HTTPBearer(auto_error=False)


def _invalid_credentials() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


async def get_current_principal(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
) -> Principal:
    """Resolve a JWT user ID into fresh server-side authorization facts."""

    if credentials is None:
        raise _invalid_credentials()
    try:
        claims = decode_access_token(credentials.credentials, settings=get_settings())
        user = await db_session.get(User, claims.user_id)
    except InvalidAccessToken as error:
        raise _invalid_credentials() from error
    if user is None or not user.is_active:
        raise _invalid_credentials()
    return _issue_principal(user_id=user.id, is_platform_admin=user.is_platform_admin)


async def require_platform_principal(
    principal: Annotated[Principal, Depends(get_current_principal)],
) -> Principal:
    """Require a current platform administrator; JWT claims are not trusted for this."""

    if not principal.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform access required",
        )
    return principal


async def get_tenant_context(
    merchant_id: int,
    principal: Annotated[Principal, Depends(get_current_principal)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
) -> TenantContext:
    """Validate the requested merchant against the current membership relation."""

    try:
        return await TenantContextFactory(session=db_session).for_merchant(
            principal=principal,
            merchant_id=merchant_id,
        )
    except TenantAccessDenied as error:
        record_security_event(
            "tenancy.access_denied",
            result="denied",
            user_id=principal.user_id,
            failure_reason="inactive_or_missing_membership",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Merchant access denied",
        ) from error


async def scoped_tenant_context(
    context: Annotated[TenantContext, Depends(get_tenant_context)],
) -> AsyncIterator[TenantContext]:
    """FastAPI dependency that holds the ORM tenant filter for one request."""

    with tenant_scope(context):
        yield context
