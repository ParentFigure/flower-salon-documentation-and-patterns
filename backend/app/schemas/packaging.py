from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PackagingCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=1000)
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    is_active: bool = True

    model_config = ConfigDict(str_strip_whitespace=True)


class PackagingUpdate(PackagingCreate):
    pass


class PackagingRead(BaseModel):
    id: int
    name: str
    description: str | None
    price: Decimal
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
