from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Bouquet, Client, Order, OrderItem, OrderStatus, User, UserRole
from app.repositories.order_repository import OrderRepository


def build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def create_client_and_bouquet(session: Session) -> tuple[Client, Bouquet]:
    user = User(
        email="repository-client@example.com",
        password_hash="hashed-password",
        role=UserRole.CLIENT,
    )
    client = Client(user=user, full_name="Repository Client", phone="+380000000001")
    bouquet = Bouquet(
        name="Repository Roses",
        description="Bouquet for repository tests",
        base_price=Decimal("600.00"),
        is_custom=False,
    )
    session.add_all([client, bouquet])
    session.commit()
    return client, bouquet


def test_create_order_persists_order_items_and_recalculates_total():
    session = build_session()
    client, bouquet = create_client_and_bouquet(session)
    repository = OrderRepository(session)

    order = Order(
        client_id=client.id,
        discount_amount=Decimal("50.00"),
        delivery_cost=Decimal("100.00"),
        delivery_type="courier",
        delivery_address="Lviv, Test Street 10",
    )
    order.items.append(
        OrderItem(
            bouquet_id=bouquet.id,
            quantity=2,
            unit_price=Decimal("600.00"),
        )
    )

    created = repository.create(order)

    assert created.id is not None
    assert created.subtotal == Decimal("1200.00")
    assert created.total_price == Decimal("1250.00")
    assert len(created.items) == 1
    assert created.items[0].id is not None


def test_get_by_id_returns_order_with_items():
    session = build_session()
    client, bouquet = create_client_and_bouquet(session)
    repository = OrderRepository(session)

    created = repository.create(
        Order(
            client_id=client.id,
            items=[
                OrderItem(
                    bouquet_id=bouquet.id,
                    quantity=1,
                    unit_price=Decimal("600.00"),
                )
            ],
        )
    )

    found = repository.get_by_id(created.id)

    assert found is not None
    assert found.id == created.id
    assert len(found.items) == 1
    assert found.items[0].bouquet_id == bouquet.id


def test_get_by_id_returns_none_for_missing_order():
    session = build_session()
    repository = OrderRepository(session)

    assert repository.get_by_id(9999) is None


def test_list_for_client_returns_only_clients_orders_newest_first():
    session = build_session()
    client, bouquet = create_client_and_bouquet(session)

    other_user = User(
        email="other-client@example.com",
        password_hash="hashed-password",
        role=UserRole.CLIENT,
    )
    other_client = Client(user=other_user, full_name="Other Client")
    session.add(other_client)
    session.commit()

    repository = OrderRepository(session)
    first = repository.create(
        Order(
            client_id=client.id,
            items=[OrderItem(bouquet_id=bouquet.id, quantity=1, unit_price=Decimal("600.00"))],
        )
    )
    second = repository.create(
        Order(
            client_id=client.id,
            items=[OrderItem(bouquet_id=bouquet.id, quantity=2, unit_price=Decimal("600.00"))],
        )
    )
    repository.create(
        Order(
            client_id=other_client.id,
            items=[OrderItem(bouquet_id=bouquet.id, quantity=1, unit_price=Decimal("600.00"))],
        )
    )

    orders = repository.list_for_client(client.id)

    assert [order.id for order in orders] == [second.id, first.id]


def test_update_status_changes_persisted_order_status():
    session = build_session()
    client, _ = create_client_and_bouquet(session)
    repository = OrderRepository(session)
    order = repository.create(Order(client_id=client.id))

    updated = repository.update_status(order.id, OrderStatus.CONFIRMED)

    assert updated is not None
    assert updated.status == OrderStatus.CONFIRMED
    assert repository.get_by_id(order.id).status == OrderStatus.CONFIRMED


def test_update_status_returns_none_for_missing_order():
    session = build_session()
    repository = OrderRepository(session)

    assert repository.update_status(9999, OrderStatus.CONFIRMED) is None
