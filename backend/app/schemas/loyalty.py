from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.loyalty_card import LoyaltyCardType


class LoyaltyCardIssue(BaseModel):
    client_id: int = Field(gt=0)
    card_type: LoyaltyCardType = LoyaltyCardType.BONUS


class LoyaltyCardUpdate(BaseModel):
    card_type: LoyaltyCardType
    is_active: bool = True


class BonusAmount(BaseModel):
    amount: Decimal = Field(
        gt=0,
        max_digits=10,
        decimal_places=2,
    )


class LoyaltyCardRead(BaseModel):
    id: int
    client_id: int
    card_type: LoyaltyCardType
    bonus_balance: Decimal
    is_active: bool
    issued_at: datetime
    discount_percent: Decimal
    free_delivery: bool

    model_config = ConfigDict(from_attributes=True)


class BonusBalanceRead(BaseModel):
    client_id: int
    bonus_balance: Decimal
