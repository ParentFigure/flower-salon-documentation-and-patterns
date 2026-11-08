from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import DeliveryMethod, Order, Salon
from app.repositories import DeliveryMethodRepository, SalonRepository


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_salon_repository_creates_and_finds_branch():
    with make_session() as db:
        repo = SalonRepository(db)
        salon = repo.create(
            Salon(
                name="Flower Salon — Center",
                address="1 Rynok Square, Lviv",
                phone="+380000000001",
            )
        )

        found = repo.get_by_name("Flower Salon — Center")
        assert found is not None
        assert found.id == salon.id
        assert found.address == "1 Rynok Square, Lviv"


def test_salon_active_only_filter():
    with make_session() as db:
        repo = SalonRepository(db)
        repo.create(Salon(name="Center", address="Center address"))
        repo.create(Salon(name="Closed branch", address="Old address", is_active=False))

        assert [salon.name for salon in repo.list_all(active_only=True)] == ["Center"]


def test_salon_name_is_unique():
    with make_session() as db:
        db.add_all(
            [
                Salon(name="Center", address="Address 1"),
                Salon(name="Center", address="Address 2"),
            ]
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        else:
            raise AssertionError("Salon name must be unique")


def test_delivery_repository_supports_required_delivery_variants():
    with make_session() as db:
        repo = DeliveryMethodRepository(db)
        repo.create(
            DeliveryMethod(
                code="pickup",
                name="Pickup",
                base_price=Decimal("0.00"),
                requires_address=False,
            )
        )
        repo.create(
            DeliveryMethod(
                code="courier",
                name="Courier delivery",
                base_price=Decimal("100.00"),
                requires_address=True,
            )
        )
        repo.create(
            DeliveryMethod(
                code="express",
                name="Express delivery",
                base_price=Decimal("200.00"),
                requires_address=True,
            )
        )

        assert {method.code for method in repo.list_all()} == {
            "pickup",
            "courier",
            "express",
        }
        assert repo.get_by_code("courier").requires_address is True


def test_delivery_method_active_only_filter():
    with make_session() as db:
        repo = DeliveryMethodRepository(db)
        repo.create(DeliveryMethod(code="pickup", name="Pickup"))
        repo.create(
            DeliveryMethod(
                code="old",
                name="Old delivery",
                is_active=False,
            )
        )

        assert [method.code for method in repo.list_all(active_only=True)] == ["pickup"]


def test_delivery_method_price_cannot_be_negative():
    with make_session() as db:
        db.add(
            DeliveryMethod(
                code="invalid",
                name="Invalid delivery",
                base_price=Decimal("-1.00"),
            )
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        else:
            raise AssertionError("Negative delivery price must violate DB constraint")


def test_delivery_method_code_is_unique():
    with make_session() as db:
        db.add_all(
            [
                DeliveryMethod(code="courier", name="Courier 1"),
                DeliveryMethod(code="courier", name="Courier 2"),
            ]
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        else:
            raise AssertionError("Delivery method code must be unique")


def test_order_can_reference_delivery_method_and_pickup_salon():
    with make_session() as db:
        salon = Salon(name="Center", address="1 Rynok Square")
        method = DeliveryMethod(code="pickup", name="Pickup")
        order = Order(
            client_id=1,
            delivery_type="pickup",
            delivery_method=method,
            pickup_salon=salon,
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        assert order.delivery_method.code == "pickup"
        assert order.pickup_salon.name == "Center"
        assert order.delivery_method_id == method.id
        assert order.pickup_salon_id == salon.id
