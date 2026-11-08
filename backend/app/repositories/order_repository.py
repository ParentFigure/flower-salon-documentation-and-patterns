from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.order import Order, OrderStatus


class OrderRepository:
    """Data-access layer for Order entities."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, order: Order) -> Order:
        """Persist a new order together with its order items."""
        order.recalculate_totals()
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def get_by_id(self, order_id: int) -> Order | None:
        """Return one order with its items loaded."""
        statement = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order_id)
        )
        return self.db.scalar(statement)

    def list_for_client(self, client_id: int) -> list[Order]:
        """Return all orders of a client, newest first."""
        statement = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.client_id == client_id)
            .order_by(Order.created_at.desc(), Order.id.desc())
        )
        return list(self.db.scalars(statement).all())

    def list_all(self) -> list[Order]:
        """Return all orders, newest first, for administrative views."""
        statement = (
            select(Order)
            .options(selectinload(Order.items))
            .order_by(Order.created_at.desc(), Order.id.desc())
        )
        return list(self.db.scalars(statement).all())

    def update_status(self, order_id: int, status: OrderStatus) -> Order | None:
        """Update persisted order status and return the updated order."""
        order = self.db.get(Order, order_id)
        if order is None:
            return None

        order.status = status
        self.db.commit()
        self.db.refresh(order)
        return order
