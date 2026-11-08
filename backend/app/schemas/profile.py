from pydantic import BaseModel, Field, field_validator

from app.schemas.loyalty import LoyaltyCardRead
from app.schemas.order import OrderRead


class ClientProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=30)

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Full name cannot be empty")
        return cleaned

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class ClientProfileRead(BaseModel):
    user_id: int
    client_id: int
    email: str
    full_name: str
    phone: str | None
    loyalty_card: LoyaltyCardRead | None
    bonus_balance: str
    total_orders: int
    recent_orders: list[OrderRead]
    unread_notifications_count: int
