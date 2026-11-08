from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.flower import Flower


class FlowerRepository:
    """Data-access layer for Flower entities."""

    def __init__(self, db: Session):
        self.db = db

    def list_all(self) -> list[Flower]:
        statement = select(Flower).order_by(Flower.id)
        return list(self.db.scalars(statement).all())

    def get_by_id(self, flower_id: int) -> Flower | None:
        return self.db.get(Flower, flower_id)

    def get_by_name(self, name: str) -> Flower | None:
        statement = select(Flower).where(Flower.name == name)
        return self.db.scalar(statement)

    def create(self, flower: Flower) -> Flower:
        self.db.add(flower)
        self.db.commit()
        self.db.refresh(flower)
        return flower

    def update(self, flower: Flower, **changes) -> Flower:
        for field, value in changes.items():
            setattr(flower, field, value)
        self.db.commit()
        self.db.refresh(flower)
        return flower

    def delete(self, flower: Flower) -> None:
        self.db.delete(flower)
        self.db.commit()
