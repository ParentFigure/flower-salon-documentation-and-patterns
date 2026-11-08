from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, CheckConstraint, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class DeliveryMethod(Base):
    """Configurable delivery option stored in the database."""

    __tablename__ = "delivery_methods"
    __table_args__ = (
        CheckConstraint(
            "base_price >= 0",
            name="ck_delivery_method_price_non_negative",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    requires_address: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    orders: Mapped[list["Order"]] = relationship(back_populates="delivery_method")
