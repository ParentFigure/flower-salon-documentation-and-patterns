from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class LoyaltyCardType(str, Enum):
    GOLD = "gold"
    BONUS = "bonus"
    SOCIAL = "social"


class LoyaltyCard(Base):
    __tablename__ = "loyalty_cards"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(
        ForeignKey("clients.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    card_type: Mapped[LoyaltyCardType] = mapped_column(
        SqlEnum(LoyaltyCardType, name="loyalty_card_type", native_enum=False),
        default=LoyaltyCardType.BONUS,
        nullable=False,
    )
    bonus_balance: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    client: Mapped["Client"] = relationship(back_populates="loyalty_card")

    @property
    def free_delivery(self) -> bool:
        """Gold card holders receive free standard delivery."""
        return self.card_type == LoyaltyCardType.GOLD

    @property
    def discount_percent(self) -> Decimal:
        """Default percentage discount associated with the card type."""
        if self.card_type == LoyaltyCardType.GOLD:
            return Decimal("10.00")
        if self.card_type == LoyaltyCardType.SOCIAL:
            return Decimal("15.00")
        return Decimal("0.00")

    def add_bonus(self, amount: Decimal) -> Decimal:
        if amount <= Decimal("0.00"):
            raise ValueError("Bonus amount must be positive")

        current = self.bonus_balance or Decimal("0.00")
        self.bonus_balance = current + amount
        return self.bonus_balance

    def spend_bonus(self, amount: Decimal) -> Decimal:
        if amount <= Decimal("0.00"):
            raise ValueError("Bonus amount must be positive")

        current = self.bonus_balance or Decimal("0.00")
        if amount > current:
            raise ValueError("Not enough bonuses")

        self.bonus_balance = current - amount
        return self.bonus_balance
