from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.order import OrderStatus
from app.schemas.custom_bouquet import CustomBouquetCreate


class DeliveryType(str, Enum):
    PICKUP = "pickup"
    COURIER = "courier"
    EXPRESS = "express"


class DiscountType(str, Enum):
    NONE = "none"
    GOLD = "gold"
    SOCIAL = "social"
    EVENT = "event"
    BONUS = "bonus"


class OrderItemCreate(BaseModel):
    bouquet_id: int | None = Field(default=None, gt=0)
    custom_bouquet: CustomBouquetCreate | None = None
    quantity: int = Field(gt=0, le=100)

    @model_validator(mode="after")
    def validate_item_source(self):
        has_catalog_bouquet = self.bouquet_id is not None
        has_custom_bouquet = self.custom_bouquet is not None

        if has_catalog_bouquet == has_custom_bouquet:
            raise ValueError(
                "Exactly one of bouquet_id or custom_bouquet must be provided"
            )
        return self


class OrderCreate(BaseModel):
    client_id: int = Field(gt=0)
    items: list[OrderItemCreate] = Field(min_length=1)
    delivery_type: DeliveryType = DeliveryType.PICKUP
    delivery_method_id: int | None = Field(default=None, gt=0)
    pickup_salon_id: int | None = Field(default=None, gt=0)
    delivery_address: str | None = Field(default=None, max_length=255)
    discount_type: DiscountType = DiscountType.NONE
    event_name: str | None = Field(default=None, max_length=120)
    discount_percent: Decimal | None = Field(
        default=None,
        ge=0,
        le=100,
        max_digits=5,
        decimal_places=2,
    )
    bonuses_to_use: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=10,
        decimal_places=2,
    )


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderItemRead(BaseModel):
    id: int
    bouquet_id: int | None
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    item_name: str | None
    item_description: str | None
    is_custom: bool
    customization: dict | None

    model_config = ConfigDict(from_attributes=True)


class OrderRead(BaseModel):
    id: int
    client_id: int
    status: OrderStatus
    subtotal: Decimal
    discount_amount: Decimal
    delivery_cost: Decimal
    total_price: Decimal
    delivery_type: str
    delivery_method_id: int | None
    pickup_salon_id: int | None
    delivery_address: str | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemRead]

    model_config = ConfigDict(from_attributes=True)
