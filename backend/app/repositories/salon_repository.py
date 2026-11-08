from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.salon import Salon


class SalonRepository:
    """Data-access layer for flower salons in the network."""

    def __init__(self, db: Session):
        self.db = db

    def list_all(self, active_only: bool = False) -> list[Salon]:
        statement = select(Salon).order_by(Salon.name)
        if active_only:
            statement = statement.where(Salon.is_active.is_(True))
        return list(self.db.scalars(statement).all())

    def get_by_id(self, salon_id: int) -> Salon | None:
        return self.db.get(Salon, salon_id)

    def get_by_name(self, name: str) -> Salon | None:
        return self.db.scalar(select(Salon).where(Salon.name == name))

    def create(self, salon: Salon) -> Salon:
        self.db.add(salon)
        self.db.commit()
        self.db.refresh(salon)
        return salon

    def update(self, salon: Salon, **changes) -> Salon:
        for field, value in changes.items():
            setattr(salon, field, value)
        self.db.commit()
        self.db.refresh(salon)
        return salon

    def delete(self, salon: Salon) -> None:
        self.db.delete(salon)
        self.db.commit()
