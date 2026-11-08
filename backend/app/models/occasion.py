from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


bouquet_occasions = Table(
    "bouquet_occasions",
    Base.metadata,
    Column(
        "bouquet_id",
        ForeignKey("bouquets.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "occasion_id",
        ForeignKey("occasions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Occasion(Base):
    __tablename__ = "occasions"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    bouquets: Mapped[list["Bouquet"]] = relationship(
        secondary=bouquet_occasions,
        back_populates="occasions",
    )
