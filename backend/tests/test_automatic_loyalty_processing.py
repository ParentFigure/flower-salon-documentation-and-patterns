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
    User,
    UserRole,
)
from app.patterns.strategy.delivery import PickupDelivery
from app.patterns.strategy.discount import GoldDiscount
from app.repositories.loyalty_card_repository import LoyaltyCardRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.order_repository import OrderRepository
from app.services.loyalty_service import LoyaltyService
from app.services.order_service import OrderService


def build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_completed_order_accrues_bonus_and_persists_notification():
    session = build_session()
    client = Client(
        user=User(
            email="complete-loyalty@example.com",
            password_hash="hashed",
            role=UserRole.CLIENT,
        ),
        full_name="Completion Loyalty Client",
    )
    bouquet = Bouquet(
        name="Completion Roses",
        base_price=Decimal("1000.00"),
        is_custom=False,
    )
    session.add_all([client, bouquet])
    session.commit()

    notification_repository = NotificationRepository(session)
    loyalty_service = LoyaltyService(
        LoyaltyCardRepository(session),
        notification_repository=notification_repository,
    )
    loyalty_service.issue_card(client.id, LoyaltyCardType.GOLD)

    order_service = OrderService(
        OrderRepository(session),
        notification_repository=notification_repository,
        loyalty_service=loyalty_service,
    )
    order = order_service.create_order(
        client_id=client.id,
        items=[
            OrderItem(
                bouquet_id=bouquet.id,
                quantity=1,
                unit_price=Decimal("1000.00"),
            )
        ],
        delivery_strategy=PickupDelivery(),
        discount_strategy=GoldDiscount(),
    )

    order_service.confirm_order(order.id)
    order_service.start_preparing(order.id)
    order_service.mark_ready(order.id)
    order_service.start_delivery(order.id)
    completed = order_service.complete_order(order.id)

    card = loyalty_service.get_card(client.id)
    notifications = notification_repository.list_for_client(client.id)

    assert completed.total_price == Decimal("900.00")
    assert card.bonus_balance == Decimal("45.00")
    assert [item.type for item in notifications].count(NotificationType.BONUS_ACCRUED) == 1
    assert any("45.00" in item.message for item in notifications)


def test_completed_order_without_loyalty_card_does_not_fail():
    session = build_session()
    client = Client(
        user=User(
            email="complete-no-card@example.com",
            password_hash="hashed",
            role=UserRole.CLIENT,
        ),
        full_name="No Card Client",
    )
    bouquet = Bouquet(
        name="No Card Roses",
        base_price=Decimal("500.00"),
        is_custom=False,
    )
    session.add_all([client, bouquet])
    session.commit()

    notification_repository = NotificationRepository(session)
    loyalty_service = LoyaltyService(
        LoyaltyCardRepository(session),
        notification_repository=notification_repository,
    )
    order_service = OrderService(
        OrderRepository(session),
        notification_repository=notification_repository,
        loyalty_service=loyalty_service,
    )
    order = order_service.create_order(
        client_id=client.id,
        items=[
            OrderItem(
                bouquet_id=bouquet.id,
                quantity=1,
                unit_price=Decimal("500.00"),
            )
        ],
        delivery_strategy=PickupDelivery(),
        discount_strategy=loyalty_service.automatic_discount_strategy_for(client.id),
    )

    order_service.confirm_order(order.id)
    order_service.start_preparing(order.id)
    order_service.mark_ready(order.id)
    order_service.start_delivery(order.id)
    completed = order_service.complete_order(order.id)

    assert completed.total_price == Decimal("500.00")
    assert all(
        item.type != NotificationType.BONUS_ACCRUED
        for item in notification_repository.list_for_client(client.id)
    )
