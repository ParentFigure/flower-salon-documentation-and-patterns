from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.delivery_method import DeliveryMethod


class DeliveryMethodRepository:
    """Data-access layer for configurable delivery methods."""

    def __init__(self, db: Session):
        self.db = db

    def list_all(self, active_only: bool = False) -> list[DeliveryMethod]:
        statement = select(DeliveryMethod).order_by(DeliveryMethod.name)
        if active_only:
            statement = statement.where(DeliveryMethod.is_active.is_(True))
        return list(self.db.scalars(statement).all())

    def get_by_id(self, method_id: int) -> DeliveryMethod | None:
        return self.db.get(DeliveryMethod, method_id)

    def get_by_code(self, code: str) -> DeliveryMethod | None:
        return self.db.scalar(
            select(DeliveryMethod).where(DeliveryMethod.code == code)
        )

    def get_by_name(self, name: str) -> DeliveryMethod | None:
        return self.db.scalar(
            select(DeliveryMethod).where(DeliveryMethod.name == name)
        )

    def create(self, method: DeliveryMethod) -> DeliveryMethod:
        self.db.add(method)
        self.db.commit()
        self.db.refresh(method)
        return method

    def update(self, method: DeliveryMethod, **changes) -> DeliveryMethod:
        for field, value in changes.items():
            setattr(method, field, value)
        self.db.commit()
        self.db.refresh(method)
        return method

    def delete(self, method: DeliveryMethod) -> None:
        self.db.delete(method)
        self.db.commit()
