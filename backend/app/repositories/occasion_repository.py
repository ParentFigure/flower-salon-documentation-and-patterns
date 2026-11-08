from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.occasion import Occasion


class OccasionRepository:
    """Data-access layer for Occasion entities."""

    def __init__(self, db: Session):
        self.db = db

    def list_all(self, active_only: bool = False) -> list[Occasion]:
        statement = select(Occasion).order_by(Occasion.name)
        if active_only:
            statement = statement.where(Occasion.is_active.is_(True))
        return list(self.db.scalars(statement).all())

    def get_by_id(self, occasion_id: int) -> Occasion | None:
        return self.db.get(Occasion, occasion_id)

    def get_by_slug(self, slug: str) -> Occasion | None:
        statement = select(Occasion).where(Occasion.slug == slug)
        return self.db.scalar(statement)

    def create(self, occasion: Occasion) -> Occasion:
        self.db.add(occasion)
        self.db.commit()
        self.db.refresh(occasion)
        return occasion
