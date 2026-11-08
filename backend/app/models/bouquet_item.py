from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BouquetItem(Base):
    """A flower and its quantity inside a catalog bouquet."""

    __tablename__ = "bouquet_items"
    __table_args__ = (
        UniqueConstraint("bouquet_id", "flower_id", name="uq_bouquet_item_flower"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bouquet_id: Mapped[int] = mapped_column(
        ForeignKey("bouquets.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    flower_id: Mapped[int] = mapped_column(
        ForeignKey("flowers.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)

    bouquet: Mapped["Bouquet"] = relationship(back_populates="items")
    flower: Mapped["Flower"] = relationship(back_populates="bouquet_items")
