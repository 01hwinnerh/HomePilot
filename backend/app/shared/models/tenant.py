from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column


class MerchantOwnedMixin:
    """Marks a model as belonging to exactly one merchant tenant."""

    merchant_id: Mapped[int] = mapped_column(
        ForeignKey("merchants.id"),
        nullable=False,
        index=True,
    )
