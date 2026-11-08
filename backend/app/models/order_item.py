from __future__ import annotations

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    bouquet_id: Mapped[int | None] = mapped_column(
        ForeignKey("bouquets.id"),
        nullable=True,
        index=True,
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # Snapshot fields preserve what the customer actually ordered even if the
    # catalog changes later. They are especially important for custom bouquets,
    # which are intentionally not persisted in the public bouquet catalog.
    item_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    item_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    customization: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    order: Mapped["Order"] = relationship(back_populates="items")
    bouquet: Mapped["Bouquet | None"] = relationship()

    @property
    def line_total(self) -> Decimal:
        return self.unit_price * self.quantity
