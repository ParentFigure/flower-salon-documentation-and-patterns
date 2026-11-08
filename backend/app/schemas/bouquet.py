from decimal import Decimal
from pydantic import BaseModel, ConfigDict

class BouquetRead(BaseModel):
    id: int
    name: str
    description: str | None
    base_price: Decimal
    is_custom: bool
    model_config = ConfigDict(from_attributes=True)
