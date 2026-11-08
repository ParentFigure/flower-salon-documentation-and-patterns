from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Bouquet, Client, OrderItem, OrderStatus, User, UserRole
from app.patterns.observer.notification_observer import (
    ClientNotificationObserver,
    NotificationPublisher,
    NotificationType,
)
from app.patterns.state.order_state import InvalidOrderStateTransition
from app.patterns.strategy.delivery import CourierDelivery, PickupDelivery
from app.patterns.strategy.discount import GoldDiscount, NoDiscount
from app.repositories.order_repository import OrderRepository
from app.services.order_service import OrderNotFoundError, OrderService


def build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def seed_client_and_bouquet(session: Session) -> tuple[Client, Bouquet]:
    user = User(
        email="service-client@example.com",
        password_hash="hashed-password",
        role=UserRole.CLIENT,
    )
    client = Client(user=user, full_name="Service Client", phone="+380000000010")
    bouquet = Bouquet(
        name="Service Roses",
        description="Bouquet used by order service tests",
        base_price=Decimal("500.00"),
        is_custom=False,
    )
    session.add_all([client, bouquet])
    session.commit()
    return client, bouquet


def make_item(bouquet: Bouquet, quantity: int = 2) -> OrderItem:
    return OrderItem(
        bouquet_id=bouquet.id,
        quantity=quantity,
        unit_price=Decimal("500.00"),
    )


def test_create_order_combines_discount_and_delivery_strategies():
    session = build_session()
    client, bouquet = seed_client_and_bouquet(session)
    service = OrderService(OrderRepository(session))

    order = service.create_order(
        client_id=client.id,
        items=[make_item(bouquet)],
        delivery_strategy=CourierDelivery(Decimal("100.00")),
        discount_strategy=GoldDiscount(Decimal("10.00")),
        delivery_address="Lviv, Green Street 5",
    )

    assert order.subtotal == Decimal("1000.00")
    assert order.discount_amount == Decimal("100.00")
    assert order.delivery_cost == Decimal("100.00")
    assert order.total_price == Decimal("1000.00")
    assert order.delivery_type == "courier"
    assert order.delivery_address == "Lviv, Green Street 5"


def test_pickup_order_does_not_require_address():
    session = build_session()
    client, bouquet = seed_client_and_bouquet(session)
    service = OrderService(OrderRepository(session))

    order = service.create_order(
        client_id=client.id,
        items=[make_item(bouquet, quantity=1)],
        delivery_strategy=PickupDelivery(),
        discount_strategy=NoDiscount(),
    )

    assert order.delivery_type == "pickup"
    assert order.delivery_cost == Decimal("0.00")
    assert order.delivery_address is None
    assert order.total_price == Decimal("500.00")


def test_courier_order_requires_delivery_address():
    session = build_session()
    client, bouquet = seed_client_and_bouquet(session)
    service = OrderService(OrderRepository(session))

    with pytest.raises(ValueError, match="Delivery address is required"):
        service.create_order(
            client_id=client.id,
            items=[make_item(bouquet)],
            delivery_strategy=CourierDelivery(),
            discount_strategy=NoDiscount(),
        )


def test_order_must_contain_at_least_one_item():
    session = build_session()
    client, _ = seed_client_and_bouquet(session)
    service = OrderService(OrderRepository(session))

    with pytest.raises(ValueError, match="at least one item"):
        service.create_order(
            client_id=client.id,
            items=[],
            delivery_strategy=PickupDelivery(),
            discount_strategy=NoDiscount(),
        )


def test_valid_state_transitions_are_persisted_and_ready_notifies_observer():
    session = build_session()
    client, bouquet = seed_client_and_bouquet(session)
    publisher = NotificationPublisher()
    observer = ClientNotificationObserver(client.id)
    publisher.subscribe(observer)
    service = OrderService(OrderRepository(session), publisher)

    order = service.create_order(
        client_id=client.id,
        items=[make_item(bouquet, quantity=1)],
        delivery_strategy=PickupDelivery(),
        discount_strategy=NoDiscount(),
    )

    assert service.confirm_order(order.id).status == OrderStatus.CONFIRMED
    assert service.start_preparing(order.id).status == OrderStatus.PREPARING
    assert service.mark_ready(order.id).status == OrderStatus.READY

    assert len(observer.events) == 1
    assert observer.events[0].type == NotificationType.ORDER_READY
    assert f"#{order.id}" in observer.events[0].message


def test_invalid_state_transition_is_rejected():
    session = build_session()
    client, bouquet = seed_client_and_bouquet(session)
    service = OrderService(OrderRepository(session))
    order = service.create_order(
        client_id=client.id,
        items=[make_item(bouquet, quantity=1)],
        delivery_strategy=PickupDelivery(),
        discount_strategy=NoDiscount(),
    )

    with pytest.raises(InvalidOrderStateTransition):
        service.mark_ready(order.id)


def test_missing_order_raises_domain_friendly_error():
    session = build_session()
    service = OrderService(OrderRepository(session))

    with pytest.raises(OrderNotFoundError, match="#9999"):
        service.confirm_order(9999)
