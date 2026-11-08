from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class FlowerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    unit_price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    stock_qty: int = Field(default=0, ge=0)


class FlowerUpdate(FlowerCreate):
    pass


class FlowerRead(BaseModel):
    id: int
    name: str
    unit_price: Decimal
    stock_qty: int

    model_config = ConfigDict(from_attributes=True)
