from __future__ import annotations

from decimal import Decimal

from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.patterns.observer.notification_observer import (
    NotificationPublisher,
    PersistentNotificationObserver,
)
from app.patterns.state.order_state import (
    CancelledState,
    CompletedState,
    ConfirmedState,
    CreatedState,
    DeliveringState,
    OrderStateContext,
    PreparingState,
    ReadyState,
)
from app.patterns.strategy.delivery import DeliveryCostCalculator, DeliveryStrategy
from app.patterns.strategy.discount import BonusDiscount, DiscountCalculator, DiscountStrategy
from app.repositories.notification_repository import NotificationRepository
from app.repositories.order_repository import OrderRepository
from app.services.loyalty_service import LoyaltyService


class OrderNotFoundError(LookupError):
    """Raised when a requested order does not exist."""


_STATE_BY_STATUS = {
    OrderStatus.CREATED: CreatedState,
    OrderStatus.CONFIRMED: ConfirmedState,
    OrderStatus.PREPARING: PreparingState,
    OrderStatus.READY: ReadyState,
    OrderStatus.DELIVERING: DeliveringState,
    OrderStatus.COMPLETED: CompletedState,
    OrderStatus.CANCELLED: CancelledState,
}


class OrderService:
    """Application service that coordinates order-related business rules."""

    def __init__(
        self,
        repository: OrderRepository,
        notifications: NotificationPublisher | None = None,
        notification_repository: NotificationRepository | None = None,
        loyalty_service: LoyaltyService | None = None,
    ) -> None:
        self.repository = repository
        self.notifications = notifications or NotificationPublisher()
        self.notification_repository = notification_repository
        self.loyalty_service = loyalty_service

    def create_order(
        self,
        *,
        client_id: int,
        items: list[OrderItem],
        delivery_strategy: DeliveryStrategy,
        discount_strategy: DiscountStrategy,
        delivery_address: str | None = None,
        delivery_method_id: int | None = None,
        pickup_salon_id: int | None = None,
    ) -> Order:
        if client_id <= 0:
            raise ValueError("Client id must be greater than zero")
        if not items:
            raise ValueError("Order must contain at least one item")

        for item in items:
            if item.quantity <= 0:
                raise ValueError("Order item quantity must be greater than zero")
            if item.unit_price < Decimal("0.00"):
                raise ValueError("Order item price cannot be negative")

        subtotal = sum((item.line_total for item in items), start=Decimal("0.00"))

        discount_calculator = DiscountCalculator(discount_strategy)
        discounted_total = discount_calculator.calculate(subtotal)
        discount_amount = subtotal - discounted_total

        delivery_calculator = DeliveryCostCalculator(delivery_strategy)
        delivery_cost = delivery_calculator.calculate(discounted_total)

        normalized_address = delivery_address.strip() if delivery_address else None
        if delivery_strategy.name != "pickup" and not normalized_address:
            raise ValueError("Delivery address is required for courier delivery")

        order = Order(
            client_id=client_id,
            items=items,
            discount_amount=discount_amount,
            delivery_cost=delivery_cost,
            delivery_type=delivery_strategy.name,
            delivery_method_id=delivery_method_id,
            pickup_salon_id=pickup_salon_id,
            delivery_address=normalized_address,
        )
        saved_order = self.repository.create(order)

        # Bonus discounts use real loyalty balance rather than a client-provided
        # arbitrary discount amount. Spend exactly the amount actually applied.
        if (
            self.loyalty_service is not None
            and isinstance(discount_strategy, BonusDiscount)
            and discount_amount > Decimal("0.00")
        ):
            self.loyalty_service.spend_bonus(client_id, discount_amount)

        return saved_order

    def get_order(self, order_id: int) -> Order:
        order = self.repository.get_by_id(order_id)
        if order is None:
            raise OrderNotFoundError(f"Order #{order_id} was not found")
        return order

    def list_client_orders(self, client_id: int) -> list[Order]:
        if client_id <= 0:
            raise ValueError("Client id must be greater than zero")
        return self.repository.list_for_client(client_id)

    def confirm_order(self, order_id: int) -> Order:
        return self._transition(order_id, "confirm")

    def start_preparing(self, order_id: int) -> Order:
        return self._transition(order_id, "start_preparing")

    def mark_ready(self, order_id: int) -> Order:
        order = self._transition(order_id, "mark_ready")
        self._notify_order_ready(order)
        return order

    def start_delivery(self, order_id: int) -> Order:
        return self._transition(order_id, "start_delivery")

    def complete_order(self, order_id: int) -> Order:
        order = self._transition(order_id, "complete")
        self._accrue_completion_bonus(order)
        return order

    def cancel_order(self, order_id: int) -> Order:
        return self._transition(order_id, "cancel")

    def _accrue_completion_bonus(self, order: Order) -> None:
        if self.loyalty_service is None:
            return
        self.loyalty_service.accrue_order_bonus(
            order.client_id,
            order.subtotal,
            order.discount_amount,
        )

    def _notify_order_ready(self, order: Order) -> None:
        persistent_observer = None
        if self.notification_repository is not None:
            persistent_observer = PersistentNotificationObserver(
                order.client_id,
                self.notification_repository,
            )
            self.notifications.subscribe(persistent_observer)

        try:
            self.notifications.order_ready(order.id)
        finally:
            if persistent_observer is not None:
                self.notifications.unsubscribe(persistent_observer)

    def _transition(self, order_id: int, action: str) -> Order:
        order = self.get_order(order_id)
        state_class = _STATE_BY_STATUS[order.status]
        context = OrderStateContext(state_class())

        transition = getattr(context, action)
        transition()

        new_status = OrderStatus(context.status)
        updated = self.repository.update_status(order.id, new_status)
        if updated is None:  # Defensive guard: the order existed a moment ago.
            raise OrderNotFoundError(f"Order #{order_id} was not found")
        return updated
