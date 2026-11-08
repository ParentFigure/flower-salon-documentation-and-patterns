from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.packaging import Packaging


class PackagingRepository:
    """Data-access layer for packaging options."""

    def __init__(self, db: Session):
        self.db = db

    def list_all(self, active_only: bool = False) -> list[Packaging]:
        statement = select(Packaging).order_by(Packaging.name)
        if active_only:
            statement = statement.where(Packaging.is_active.is_(True))
        return list(self.db.scalars(statement).all())

    def get_by_id(self, packaging_id: int) -> Packaging | None:
        return self.db.get(Packaging, packaging_id)

    def get_by_name(self, name: str) -> Packaging | None:
        statement = select(Packaging).where(Packaging.name == name)
        return self.db.scalar(statement)

    def create(self, packaging: Packaging) -> Packaging:
        self.db.add(packaging)
        self.db.commit()
        self.db.refresh(packaging)
        return packaging
