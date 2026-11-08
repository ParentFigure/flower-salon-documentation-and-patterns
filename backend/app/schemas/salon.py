from pydantic import BaseModel, ConfigDict, Field


class SalonCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    address: str = Field(min_length=5, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool = True

    model_config = ConfigDict(str_strip_whitespace=True)


class SalonUpdate(SalonCreate):
    pass


class SalonRead(BaseModel):
    id: int
    name: str
    address: str
    phone: str | None
    description: str | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
