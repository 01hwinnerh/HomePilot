from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_principal
from app.core.config import Settings, get_settings
from app.core.database import get_db_session
from app.core.redis import get_redis
from app.core.security import (
    csrf_tokens_match,
    hash_refresh_token,
)
from app.modules.identity.rate_limit import AuthRateLimiter, AuthRateLimitExceeded
from app.modules.identity.schemas import (
    AuthResponse,
    CurrentUserResponse,
    LoginRequest,
    MerchantMembershipResponse,
    RegisterRequest,
)
from app.modules.identity.service import (
    AuthResult,
    AuthService,
    DuplicateEmail,
    InvalidCredentials,
    InvalidRefreshSession,
)
from app.shared.tenancy.context import Principal

router = APIRouter(prefix="/auth", tags=["auth"])
def get_auth_rate_limiter() -> AuthRateLimiter:
    """Build the request limiter from centralized settings and Redis client."""

    return AuthRateLimiter(redis=get_redis(), settings=get_settings())


def _client_ip(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


def _invalid_credentials() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")


def _too_many_requests() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail="Too many authentication attempts",
    )


def _set_auth_cookies(*, response: Response, result: AuthResult, settings: Settings) -> None:
    cookie_options = {
        "secure": settings.auth_cookie_secure,
        "samesite": settings.auth_cookie_same_site,
        "path": settings.auth_cookie_path,
    }
    response.set_cookie(
        key=settings.auth_refresh_cookie_name,
        value=result.refresh_token,
        httponly=True,
        **cookie_options,
    )
    response.set_cookie(
        key=settings.auth_csrf_cookie_name,
        value=result.csrf_token,
        httponly=False,
        **cookie_options,
    )


def _clear_auth_cookies(*, response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.auth_refresh_cookie_name,
        path=settings.auth_cookie_path,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_same_site,
    )
    response.delete_cookie(
        key=settings.auth_csrf_cookie_name,
        path=settings.auth_cookie_path,
        secure=settings.auth_cookie_secure,
        samesite=settings.auth_cookie_same_site,
    )


def _auth_response(
    result: AuthResult,
    *,
    memberships: list[MerchantMembershipResponse] | None = None,
) -> AuthResponse:
    return AuthResponse(
        access_token=result.access_token,
        user=CurrentUserResponse.model_validate(result.user).model_copy(
            update={"memberships": memberships or []}
        ),
    )


async def _enforce_rate_limit(
    *,
    request: Request,
    scope: str,
    identity: str,
    limiter: AuthRateLimiter,
) -> None:
    try:
        await limiter.check(scope=scope, identity=identity, client_ip=_client_ip(request))
    except AuthRateLimitExceeded as error:
        raise _too_many_requests() from error


def _require_csrf(
    *,
    request: Request,
    csrf_header: str | None,
    settings: Settings,
) -> None:
    if not csrf_tokens_match(
        request.cookies.get(settings.auth_csrf_cookie_name),
        csrf_header,
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid CSRF token")


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    limiter: Annotated[AuthRateLimiter, Depends(get_auth_rate_limiter)],
) -> AuthResponse:
    await _enforce_rate_limit(
        request=request,
        scope="credentials",
        identity=str(payload.email),
        limiter=limiter,
    )
    settings = get_settings()
    try:
        result = await AuthService(session=db_session, settings=settings).register(
            email=str(payload.email), password=payload.password
        )
    except DuplicateEmail as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        ) from error
    _set_auth_cookies(response=response, result=result, settings=settings)
    return _auth_response(result)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    limiter: Annotated[AuthRateLimiter, Depends(get_auth_rate_limiter)],
) -> AuthResponse:
    await _enforce_rate_limit(
        request=request,
        scope="credentials",
        identity=payload.email,
        limiter=limiter,
    )
    settings = get_settings()
    try:
        result = await AuthService(session=db_session, settings=settings).login(
            email=payload.email, password=payload.password
        )
    except InvalidCredentials as error:
        raise _invalid_credentials() from error
    _set_auth_cookies(response=response, result=result, settings=settings)
    return _auth_response(result)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    request: Request,
    response: Response,
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    limiter: Annotated[AuthRateLimiter, Depends(get_auth_rate_limiter)],
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> AuthResponse:
    settings = get_settings()
    _require_csrf(request=request, csrf_header=csrf_header, settings=settings)
    refresh_token = request.cookies.get(settings.auth_refresh_cookie_name)
    await _enforce_rate_limit(
        request=request,
        scope="refresh",
        identity=hash_refresh_token(refresh_token) if refresh_token is not None else "missing",
        limiter=limiter,
    )
    if refresh_token is None:
        raise _invalid_credentials()
    try:
        result = await AuthService(session=db_session, settings=settings).refresh(
            refresh_token=refresh_token,
            now=datetime.now(UTC),
        )
    except InvalidRefreshSession as error:
        raise _invalid_credentials() from error
    _set_auth_cookies(response=response, result=result, settings=settings)
    return _auth_response(result)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
    csrf_header: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> Response:
    settings = get_settings()
    _require_csrf(request=request, csrf_header=csrf_header, settings=settings)
    refresh_token = request.cookies.get(settings.auth_refresh_cookie_name)
    if refresh_token is not None:
        await AuthService(session=db_session, settings=settings).logout(
            refresh_token=refresh_token,
            now=datetime.now(UTC),
        )
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_auth_cookies(response=response, settings=settings)
    return response


@router.get("/me", response_model=CurrentUserResponse)
async def me(
    principal: Annotated[Principal, Depends(get_current_principal)],
    db_session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CurrentUserResponse:
    settings = get_settings()
    service = AuthService(session=db_session, settings=settings)
    user = await service.current_user(user_id=principal.user_id)
    memberships = await service.active_memberships(user_id=user.id)
    return CurrentUserResponse.model_validate(user).model_copy(
        update={
            "memberships": [
                MerchantMembershipResponse(
                    merchant_id=merchant.id,
                    merchant_name=merchant.name,
                    role=member.role.value,
                )
                for member, merchant in memberships
            ]
        }
    )
