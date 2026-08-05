from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import (
    create_access_token,
    create_csrf_token,
    create_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.modules.identity.models import AuthSession, User
from app.modules.identity.security_events import record_security_event
from app.modules.merchants.models import Merchant, MerchantMember


class DuplicateEmail(ValueError):
    """Raised when a customer attempts to register an already-used email."""


class InvalidCredentials(ValueError):
    """Raised with a deliberately uniform message for failed logins."""


class InvalidRefreshSession(ValueError):
    """Raised for expired, revoked, replayed, or inactive refresh sessions."""


@dataclass(frozen=True)
class AuthResult:
    user: User
    session: AuthSession
    access_token: str
    refresh_token: str
    csrf_token: str


class AuthService:
    """Coordinates account credentials and revocable refresh sessions."""

    def __init__(self, *, session: AsyncSession, settings: Settings) -> None:
        self._session = session
        self._settings = settings

    async def register(self, *, email: str, password: str) -> AuthResult:
        normalized_email = self._normalize_email(email)
        existing_user = await self._session.scalar(
            select(User).where(User.email == normalized_email)
        )
        if existing_user is not None:
            raise DuplicateEmail("Email already registered.")

        user = User(email=normalized_email, password_hash=hash_password(password))
        self._session.add(user)
        try:
            await self._session.flush()
            result = await self._create_auth_result(user=user, now=datetime.now(UTC))
            await self._session.commit()
        except IntegrityError as error:
            await self._session.rollback()
            raise DuplicateEmail("Email already registered.") from error
        except Exception:
            await self._session.rollback()
            raise

        record_security_event("auth.registered", result="success", user_id=user.id)
        return result

    async def login(self, *, email: str, password: str) -> AuthResult:
        normalized_email = self._normalize_email(email)
        user = await self._session.scalar(select(User).where(User.email == normalized_email))
        if user is None or not verify_password(password, user.password_hash):
            record_security_event("auth.login_failed", result="denied")
            raise InvalidCredentials("Invalid credentials")
        if not user.is_active:
            record_security_event("auth.user_inactive", result="denied", user_id=user.id)
            raise InvalidCredentials("Invalid credentials")

        try:
            result = await self._create_auth_result(user=user, now=datetime.now(UTC))
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise

        record_security_event("auth.login_succeeded", result="success", user_id=user.id)
        return result

    async def refresh(self, *, refresh_token: str, now: datetime) -> AuthResult:
        refresh_session = await self._session.scalar(
            select(AuthSession)
            .where(AuthSession.refresh_token_hash == hash_refresh_token(refresh_token))
            .with_for_update()
        )
        if refresh_session is None:
            return await self._reject_refresh("unknown_session")
        if refresh_session.revoked_at is not None or refresh_session.expires_at <= now:
            return await self._reject_refresh("revoked_or_expired", refresh_session.id)

        user = await self._session.get(User, refresh_session.user_id)
        if user is None or not user.is_active:
            return await self._reject_refresh("inactive_user", refresh_session.id, user)

        try:
            refresh_session.revoked_at = now
            refresh_session.revoked_reason = "rotated"
            result = await self._create_auth_result(user=user, now=now)
            refresh_session.replaced_by_session_id = result.session.id
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise

        record_security_event(
            "auth.refresh_succeeded",
            result="success",
            user_id=user.id,
            session_id=refresh_session.id,
        )
        return result

    async def logout(self, *, refresh_token: str, now: datetime) -> None:
        refresh_session = await self._session.scalar(
            select(AuthSession)
            .where(AuthSession.refresh_token_hash == hash_refresh_token(refresh_token))
            .with_for_update()
        )
        if refresh_session is None or refresh_session.revoked_at is not None:
            await self._session.rollback()
            return

        try:
            refresh_session.revoked_at = now
            refresh_session.revoked_reason = "logout"
            await self._session.commit()
        except Exception:
            await self._session.rollback()
            raise

        record_security_event(
            "auth.logout",
            result="success",
            user_id=refresh_session.user_id,
            session_id=refresh_session.id,
        )

    async def current_user(self, *, user_id: int) -> User:
        user = await self._session.get(User, user_id)
        if user is None or not user.is_active:
            raise InvalidCredentials("Invalid credentials")
        return user

    async def active_memberships(
        self,
        *,
        user_id: int,
    ) -> list[tuple[MerchantMember, Merchant]]:
        result = await self._session.execute(
            select(MerchantMember, Merchant)
            .join(Merchant, Merchant.id == MerchantMember.merchant_id)
            .where(
                MerchantMember.user_id == user_id,
                MerchantMember.is_active.is_(True),
                Merchant.is_active.is_(True),
            )
            .order_by(Merchant.id)
        )
        return list(result.all())

    async def _create_auth_result(self, *, user: User, now: datetime) -> AuthResult:
        refresh_token = create_refresh_token()
        auth_session = AuthSession(
            user_id=user.id,
            refresh_token_hash=hash_refresh_token(refresh_token),
            expires_at=now + timedelta(days=self._settings.auth_refresh_token_days),
        )
        self._session.add(auth_session)
        await self._session.flush()
        return AuthResult(
            user=user,
            session=auth_session,
            access_token=create_access_token(user_id=user.id, settings=self._settings),
            refresh_token=refresh_token,
            csrf_token=create_csrf_token(),
        )

    async def _reject_refresh(
        self,
        reason: str,
        session_id: int | None = None,
        user: User | None = None,
    ) -> AuthResult:
        user_id = user.id if user is not None else None
        await self._session.rollback()
        record_security_event(
            "auth.refresh_rejected",
            result="denied",
            user_id=user_id,
            session_id=session_id,
            failure_reason=reason,
        )
        raise InvalidRefreshSession("Invalid refresh session")

    @staticmethod
    def _normalize_email(email: str) -> str:
        return email.strip().casefold()
