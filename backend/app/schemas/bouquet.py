from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class BouquetCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None
    base_price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    is_custom: bool = False


class BouquetRead(BaseModel):
    id: int
    name: str
    description: str | None
    base_price: Decimal
    is_custom: bool

    model_config = ConfigDict(from_attributes=True)
