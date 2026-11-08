from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Bouquet, Client, Order, OrderItem, OrderStatus, User, UserRole


def build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def create_client_and_bouquet(session: Session) -> tuple[Client, Bouquet]:
    user = User(
        email="client@example.com",
        password_hash="hashed-password",
        role=UserRole.CLIENT,
    )
    client = Client(user=user, full_name="Marta Test", phone="+380000000000")
    bouquet = Bouquet(
        name="Birthday Roses",
        description="Test bouquet",
        base_price=Decimal("500.00"),
        is_custom=False,
    )
    session.add_all([client, bouquet])
    session.commit()
    return client, bouquet


def test_order_has_created_status_by_default():
    session = build_session()
    client, _ = create_client_and_bouquet(session)

    order = Order(client_id=client.id)
    session.add(order)
    session.commit()
    session.refresh(order)

    assert order.status == OrderStatus.CREATED
    assert order.delivery_type == "pickup"
    assert order.total_price == Decimal("0.00")


def test_order_item_keeps_purchase_price_and_calculates_line_total():
    session = build_session()
    client, bouquet = create_client_and_bouquet(session)

    order = Order(client_id=client.id)
    item = OrderItem(
        bouquet_id=bouquet.id,
        quantity=3,
        unit_price=Decimal("450.00"),
    )
    order.items.append(item)
    session.add(order)
    session.commit()

    assert item.line_total == Decimal("1350.00")

    bouquet.base_price = Decimal("700.00")
    session.commit()

    assert item.unit_price == Decimal("450.00")
    assert item.line_total == Decimal("1350.00")


def test_order_recalculates_subtotal_discount_delivery_and_total():
    session = build_session()
    client, bouquet = create_client_and_bouquet(session)

    order = Order(
        client_id=client.id,
        discount_amount=Decimal("100.00"),
        delivery_cost=Decimal("80.00"),
        delivery_type="courier",
        delivery_address="Lviv, Test Street 1",
    )
    order.items.extend(
        [
            OrderItem(
                bouquet_id=bouquet.id,
                quantity=2,
                unit_price=Decimal("500.00"),
            ),
            OrderItem(
                bouquet_id=bouquet.id,
                quantity=1,
                unit_price=Decimal("250.00"),
            ),
        ]
    )

    total = order.recalculate_totals()

    assert order.subtotal == Decimal("1250.00")
    assert total == Decimal("1230.00")
    assert order.total_price == Decimal("1230.00")


def test_order_total_never_becomes_negative():
    order = Order(
        discount_amount=Decimal("1000.00"),
        delivery_cost=Decimal("0.00"),
    )

    assert order.recalculate_totals() == Decimal("0.00")
