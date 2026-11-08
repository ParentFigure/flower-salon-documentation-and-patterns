from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import (
    Bouquet,
    Client,
    LoyaltyCardType,
    NotificationType,
    OrderItem,
    OrderStatus,
    User,
    UserRole,
)
from app.patterns.observer import NotificationPublisher, PersistentNotificationObserver
from app.patterns.strategy.delivery import PickupDelivery
from app.patterns.strategy.discount import NoDiscount
from app.repositories.loyalty_card_repository import LoyaltyCardRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.order_repository import OrderRepository
from app.services.loyalty_service import LoyaltyService
from app.services.order_service import OrderService


def build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def create_client(session: Session, email: str = "persistent@example.com") -> Client:
    user = User(
        email=email,
        password_hash="hashed-password",
        role=UserRole.CLIENT,
    )
    client = Client(user=user, full_name="Persistent Notification Client")
    session.add(client)
    session.commit()
    return client


def test_persistent_observer_saves_all_supported_event_types():
    session = build_session()
    client = create_client(session)
    repository = NotificationRepository(session)
    publisher = NotificationPublisher()
    publisher.subscribe(PersistentNotificationObserver(client.id, repository))

    publisher.order_ready(12)
    publisher.bonus_accrued(Decimal("50.00"))
    publisher.new_arrival("Spring Roses")

    notifications = repository.list_for_client(client.id)
    assert {item.type for item in notifications} == {
        NotificationType.ORDER_READY,
        NotificationType.BONUS_ACCRUED,
        NotificationType.NEW_ARRIVAL,
    }
    assert all(item.is_read is False for item in notifications)


def test_order_ready_is_persisted_for_order_client():
    session = build_session()
    client = create_client(session, "order-persist@example.com")
    bouquet = Bouquet(
        name="Persistent Roses",
        base_price=Decimal("500.00"),
        is_custom=False,
    )
    session.add(bouquet)
    session.commit()

    notification_repository = NotificationRepository(session)
    service = OrderService(
        OrderRepository(session),
        notification_repository=notification_repository,
    )
    order = service.create_order(
        client_id=client.id,
        items=[
            OrderItem(
                bouquet_id=bouquet.id,
                quantity=1,
                unit_price=bouquet.base_price,
            )
        ],
        delivery_strategy=PickupDelivery(),
        discount_strategy=NoDiscount(),
    )

    service.confirm_order(order.id)
    service.start_preparing(order.id)
    ready = service.mark_ready(order.id)

    assert ready.status == OrderStatus.READY
    notifications = notification_repository.list_for_client(client.id)
    assert len(notifications) == 1
    assert notifications[0].type == NotificationType.ORDER_READY
    assert f"#{order.id}" in notifications[0].message


def test_accrued_bonus_is_persisted_for_loyalty_client():
    session = build_session()
    client = create_client(session, "bonus-persist@example.com")
    notification_repository = NotificationRepository(session)
    service = LoyaltyService(
        LoyaltyCardRepository(session),
        notification_repository=notification_repository,
    )
    service.issue_card(client.id, LoyaltyCardType.BONUS)

    card = service.accrue_bonus(client.id, Decimal("125.00"))

    assert card.bonus_balance == Decimal("125.00")
    notifications = notification_repository.list_for_client(client.id)
    assert len(notifications) == 1
    assert notifications[0].type == NotificationType.BONUS_ACCRUED
    assert "125.00" in notifications[0].message


def test_temporary_persistent_observer_is_unsubscribed_after_service_event():
    session = build_session()
    client = create_client(session, "unsubscribe-persist@example.com")
    publisher = NotificationPublisher()
    notification_repository = NotificationRepository(session)
    service = LoyaltyService(
        LoyaltyCardRepository(session),
        notifications=publisher,
        notification_repository=notification_repository,
    )
    service.issue_card(client.id, LoyaltyCardType.BONUS)

    service.accrue_bonus(client.id, Decimal("25.00"))

    assert publisher.observers == ()
    assert len(notification_repository.list_for_client(client.id)) == 1
