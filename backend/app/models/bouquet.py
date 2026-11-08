from __future__ import annotations

from decimal import Decimal
from sqlalchemy import Boolean, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Bouquet(Base):
    __tablename__ = "bouquets"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    base_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)

    occasions: Mapped[list["Occasion"]] = relationship(
        secondary="bouquet_occasions",
        back_populates="bouquets",
    )
