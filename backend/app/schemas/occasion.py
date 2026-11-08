from pydantic import BaseModel, ConfigDict, Field


class OccasionCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    slug: str = Field(
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool = True

    model_config = ConfigDict(str_strip_whitespace=True)


class OccasionUpdate(OccasionCreate):
    pass


class OccasionRead(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
