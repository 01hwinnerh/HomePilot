from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base
from app.shared.models.timestamps import TimestampMixin
from app.shared.models.utc_datetime import UTCDateTime


class User(TimestampMixin, Base):
    """An account that can be a customer, merchant member, or platform administrator."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        index=True,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_platform_admin: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class AuthSession(TimestampMixin, Base):
    """A revocable refresh-token session; plaintext tokens are never persisted."""

    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    refresh_token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        UTCDateTime(),
        nullable=True,
    )
    revoked_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    replaced_by_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("auth_sessions.id"),
        nullable=True,
    )
