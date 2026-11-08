from decimal import Decimal

from pydantic import BaseModel, Field


class CustomBouquetFlowerCreate(BaseModel):
    flower_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class CustomBouquetCreate(BaseModel):
    name: str = Field(default="Custom bouquet", min_length=2, max_length=120)
    flowers: list[CustomBouquetFlowerCreate] = Field(min_length=1)
    packaging_id: int | None = Field(default=None, gt=0)
    greeting_card_text: str | None = Field(default=None, max_length=250)
    occasion_ids: list[int] = Field(default_factory=list)


class CustomBouquetFlowerRead(BaseModel):
    flower_id: int
    flower_name: str
    quantity: int
    unit_price: Decimal


class CustomBouquetPreviewRead(BaseModel):
    name: str
    description: str
    total_price: Decimal
    is_custom: bool
    flowers: list[CustomBouquetFlowerRead]
    packaging_id: int | None
    packaging_name: str | None
    packaging_price: Decimal
    greeting_card_text: str | None
    greeting_card_price: Decimal
    occasion_ids: list[int]
