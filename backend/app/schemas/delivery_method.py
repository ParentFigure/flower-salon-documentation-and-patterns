from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class DeliveryMethodCreate(BaseModel):
    code: str = Field(
        min_length=2,
        max_length=50,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    base_price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    requires_address: bool = False
    is_active: bool = True

    model_config = ConfigDict(str_strip_whitespace=True)


class DeliveryMethodUpdate(DeliveryMethodCreate):
    pass


class DeliveryMethodRead(BaseModel):
    id: int
    code: str
    name: str
    description: str | None
    base_price: Decimal
    requires_address: bool
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
