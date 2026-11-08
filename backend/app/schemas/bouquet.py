from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class BouquetFlowerCreate(BaseModel):
    flower_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


class BouquetFlowerRead(BaseModel):
    flower_id: int
    flower_name: str
    quantity: int


class BouquetOccasionRead(BaseModel):
    id: int
    name: str
    slug: str


class BouquetCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = None
    base_price: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    is_custom: bool = False
    occasion_ids: list[int] = Field(default_factory=list)
    composition: list[BouquetFlowerCreate] = Field(default_factory=list)


class BouquetUpdate(BouquetCreate):
    pass


class BouquetRead(BaseModel):
    id: int
    name: str
    description: str | None
    base_price: Decimal
    is_custom: bool
    occasions: list[BouquetOccasionRead] = Field(default_factory=list)
    composition: list[BouquetFlowerRead] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
