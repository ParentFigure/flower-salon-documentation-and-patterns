from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.bouquet import Bouquet


class BouquetRepository:
    """Data-access layer for Bouquet entities."""

    def __init__(self, db: Session):
        self.db = db

    def list_all(self) -> list[Bouquet]:
        statement = select(Bouquet).order_by(Bouquet.id)
        return list(self.db.scalars(statement).all())

    def get_by_id(self, bouquet_id: int) -> Bouquet | None:
        return self.db.get(Bouquet, bouquet_id)

    def create(self, bouquet: Bouquet) -> Bouquet:
        self.db.add(bouquet)
        self.db.commit()
        self.db.refresh(bouquet)
        return bouquet
