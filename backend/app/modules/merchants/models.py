from enum import StrEnum

from sqlalchemy import Boolean, Enum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.base import Base
from app.shared.models.tenant import MerchantOwnedMixin
from app.shared.models.timestamps import TimestampMixin


class MerchantMemberRole(StrEnum):
    OWNER = "OWNER"
    STAFF = "STAFF"


class Merchant(TimestampMixin, Base):
    """A platform tenant that owns merchant-scoped business resources."""

    __tablename__ = "merchants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class MerchantMember(MerchantOwnedMixin, TimestampMixin, Base):
    """A user's active role inside a merchant tenant."""

    __tablename__ = "merchant_members"
    __table_args__ = (UniqueConstraint("user_id", "merchant_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    role: Mapped[MerchantMemberRole] = mapped_column(
        Enum(
            MerchantMemberRole,
            name="merchant_member_role",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
        ),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
