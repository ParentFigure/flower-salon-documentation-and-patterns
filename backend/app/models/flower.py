from decimal import Decimal
from sqlalchemy import Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Flower(Base):
    __tablename__ = "flowers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    stock_qty: Mapped[int] = mapped_column(Integer, default=0)
