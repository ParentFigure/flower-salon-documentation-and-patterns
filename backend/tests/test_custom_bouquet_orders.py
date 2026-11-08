import os
from decimal import Decimal

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Bouquet, Client, Flower, Packaging, User, UserRole


def make_client() -> tuple[TestClient, sessionmaker]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), TestingSessionLocal


def seed_client(SessionLocal) -> tuple[int, int]:
    with SessionLocal() as db:
        user = User(
            email="custom-order-client@example.com",
            password_hash="hashed-password",
            role=UserRole.CLIENT,
        )
        client = Client(user=user, full_name="Custom Order Client")
        db.add(client)
        db.commit()
        return client.id, user.id


def seed_custom_catalog(SessionLocal, *, rose_stock: int = 20):
    with SessionLocal() as db:
        rose = Flower(name="Rose", unit_price=Decimal("50.00"), stock_qty=rose_stock)
        packaging = Packaging(
            name="Gift box",
            price=Decimal("100.00"),
            is_active=True,
        )
        db.add_all([rose, packaging])
        db.commit()
        return rose.id, packaging.id


def seed_catalog_bouquet(SessionLocal) -> int:
    with SessionLocal() as db:
        bouquet = Bouquet(
            name="Catalog Roses",
            description="Ready bouquet",
            base_price=Decimal("300.00"),
            is_custom=False,
        )
        db.add(bouquet)
        db.commit()
        return bouquet.id


def headers_for(user_id: int) -> dict[str, str]:
    token = create_access_token(user_id, UserRole.CLIENT.value)
    return {"Authorization": f"Bearer {token}"}


def custom_item(rose_id: int, packaging_id: int, *, quantity: int = 1):
    return {
        "quantity": quantity,
        "custom_bouquet": {
            "name": "My Custom Roses",
            "flowers": [{"flower_id": rose_id, "quantity": 2}],
            "packaging_id": packaging_id,
            "greeting_card_text": "For you!",
            "occasion_ids": [],
        },
    }


def test_custom_bouquet_can_be_ordered_and_is_stored_as_snapshot():
    client, SessionLocal = make_client()
    client_id, user_id = seed_client(SessionLocal)
    rose_id, packaging_id = seed_custom_catalog(SessionLocal)

    with client:
        response = client.post(
            "/api/orders",
            headers=headers_for(user_id),
            json={
                "client_id": client_id,
                "items": [custom_item(rose_id, packaging_id)],
                "delivery_type": "pickup",
            },
        )

        assert response.status_code == 201
        data = response.json()
        item = data["items"][0]
        assert item["bouquet_id"] is None
        assert item["is_custom"] is True
        assert item["item_name"] == "My Custom Roses"
        assert Decimal(str(item["unit_price"])) == Decimal("225.00")
        assert Decimal(str(data["subtotal"])) == Decimal("225.00")
        assert item["customization"]["flowers"][0]["flower_name"] == "Rose"
        assert item["customization"]["packaging"]["name"] == "Gift box"
        assert item["customization"]["greeting_card"]["text"] == "For you!"

    # Custom order items must not pollute the public catalog.
    with SessionLocal() as db:
        assert list(db.scalars(select(Bouquet)).all()) == []

    app.dependency_overrides.clear()


def test_custom_order_price_is_frozen_after_catalog_prices_change():
    client, SessionLocal = make_client()
    client_id, user_id = seed_client(SessionLocal)
    rose_id, packaging_id = seed_custom_catalog(SessionLocal)
    headers = headers_for(user_id)

    with client:
        created = client.post(
            "/api/orders",
            headers=headers,
            json={
                "client_id": client_id,
                "items": [custom_item(rose_id, packaging_id)],
                "delivery_type": "pickup",
            },
        )
        assert created.status_code == 201
        order_id = created.json()["id"]
        original_price = Decimal(str(created.json()["items"][0]["unit_price"]))

        with SessionLocal() as db:
            db.get(Flower, rose_id).unit_price = Decimal("500.00")
            db.get(Packaging, packaging_id).price = Decimal("900.00")
            db.commit()

        fetched = client.get(f"/api/orders/{order_id}", headers=headers)
        assert fetched.status_code == 200
        assert Decimal(str(fetched.json()["items"][0]["unit_price"])) == original_price
        assert fetched.json()["items"][0]["customization"]["flowers"][0]["unit_price"] == "50.00"

    app.dependency_overrides.clear()


def test_custom_order_checks_stock_for_all_copies_of_bouquet():
    client, SessionLocal = make_client()
    client_id, user_id = seed_client(SessionLocal)
    rose_id, packaging_id = seed_custom_catalog(SessionLocal, rose_stock=3)

    with client:
        response = client.post(
            "/api/orders",
            headers=headers_for(user_id),
            json={
                "client_id": client_id,
                "items": [custom_item(rose_id, packaging_id, quantity=2)],
                "delivery_type": "pickup",
            },
        )

        assert response.status_code == 409
        assert "requested 4" in response.json()["detail"]
        assert "available 3" in response.json()["detail"]

    app.dependency_overrides.clear()


def test_order_item_rejects_catalog_and_custom_bouquet_at_same_time():
    client, SessionLocal = make_client()
    client_id, user_id = seed_client(SessionLocal)
    rose_id, packaging_id = seed_custom_catalog(SessionLocal)
    bouquet_id = seed_catalog_bouquet(SessionLocal)
    item = custom_item(rose_id, packaging_id)
    item["bouquet_id"] = bouquet_id

    with client:
        response = client.post(
            "/api/orders",
            headers=headers_for(user_id),
            json={
                "client_id": client_id,
                "items": [item],
                "delivery_type": "pickup",
            },
        )
        assert response.status_code == 422

    app.dependency_overrides.clear()


def test_order_can_mix_catalog_and_custom_bouquet_items():
    client, SessionLocal = make_client()
    client_id, user_id = seed_client(SessionLocal)
    rose_id, packaging_id = seed_custom_catalog(SessionLocal)
    bouquet_id = seed_catalog_bouquet(SessionLocal)

    with client:
        response = client.post(
            "/api/orders",
            headers=headers_for(user_id),
            json={
                "client_id": client_id,
                "items": [
                    {"bouquet_id": bouquet_id, "quantity": 1},
                    custom_item(rose_id, packaging_id),
                ],
                "delivery_type": "pickup",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert len(data["items"]) == 2
        assert data["items"][0]["bouquet_id"] == bouquet_id
        assert data["items"][0]["is_custom"] is False
        assert data["items"][0]["item_name"] == "Catalog Roses"
        assert data["items"][1]["bouquet_id"] is None
        assert data["items"][1]["is_custom"] is True
        assert Decimal(str(data["subtotal"])) == Decimal("525.00")

    app.dependency_overrides.clear()
