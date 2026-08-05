from datetime import datetime

from sqlalchemy.orm import Mapped, mapped_column

from app.shared.models.utc_datetime import UTCDateTime, utc_now


class TimestampMixin:
    """Adds immutable creation and ORM-maintained update timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        UTCDateTime(),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
