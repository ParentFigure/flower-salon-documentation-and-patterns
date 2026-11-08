import os
from decimal import Decimal

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Bouquet, Client, User, UserRole


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


def seed_data(TestingSessionLocal) -> tuple[int, int]:
    with TestingSessionLocal() as db:
        user = User(
            email="api-order-client@example.com",
            password_hash="hashed-password",
            role=UserRole.CLIENT,
        )
        client = Client(user=user, full_name="API Client", phone="+380000000020")
        bouquet = Bouquet(
            name="API Roses",
            description="Bouquet for API order tests",
            base_price=Decimal("500.00"),
            is_custom=False,
        )
        db.add_all([client, bouquet])
        db.commit()
        return client.id, bouquet.id


def create_order(client: TestClient, client_id: int, bouquet_id: int, **overrides):
    payload = {
        "client_id": client_id,
        "items": [{"bouquet_id": bouquet_id, "quantity": 2}],
        "delivery_type": "pickup",
        "discount_type": "none",
    }
    payload.update(overrides)
    return client.post("/api/orders", json=payload)


def test_create_order_returns_201_and_calculated_totals():
    client, SessionLocal = make_client()
    client_id, bouquet_id = seed_data(SessionLocal)

    with client:
        response = create_order(
            client,
            client_id,
            bouquet_id,
            delivery_type="courier",
            delivery_address="Lviv, Green Street 5",
            discount_type="gold",
        )

        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "created"
        assert Decimal(str(data["subtotal"])) == Decimal("1000.00")
        assert Decimal(str(data["discount_amount"])) == Decimal("100.00")
        assert Decimal(str(data["delivery_cost"])) == Decimal("100.00")
        assert Decimal(str(data["total_price"])) == Decimal("1000.00")
        assert data["items"][0]["quantity"] == 2
        assert Decimal(str(data["items"][0]["line_total"])) == Decimal("1000.00")

    app.dependency_overrides.clear()


def test_get_order_by_id():
    client, SessionLocal = make_client()
    client_id, bouquet_id = seed_data(SessionLocal)

    with client:
        created = create_order(client, client_id, bouquet_id).json()
        response = client.get(f"/api/orders/{created['id']}")

        assert response.status_code == 200
        assert response.json()["id"] == created["id"]
        assert response.json()["client_id"] == client_id

    app.dependency_overrides.clear()


def test_list_client_orders_returns_only_clients_orders():
    client, SessionLocal = make_client()
    client_id, bouquet_id = seed_data(SessionLocal)

    with client:
        create_order(client, client_id, bouquet_id)
        create_order(client, client_id, bouquet_id, items=[{"bouquet_id": bouquet_id, "quantity": 1}])

        response = client.get(f"/api/orders/client/{client_id}")

        assert response.status_code == 200
        assert len(response.json()) == 2
        assert all(order["client_id"] == client_id for order in response.json())

    app.dependency_overrides.clear()


def test_status_endpoint_uses_state_transitions():
    client, SessionLocal = make_client()
    client_id, bouquet_id = seed_data(SessionLocal)

    with client:
        order_id = create_order(client, client_id, bouquet_id).json()["id"]

        confirmed = client.patch(
            f"/api/orders/{order_id}/status",
            json={"status": "confirmed"},
        )
        preparing = client.patch(
            f"/api/orders/{order_id}/status",
            json={"status": "preparing"},
        )
        ready = client.patch(
            f"/api/orders/{order_id}/status",
            json={"status": "ready"},
        )

        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == "confirmed"
        assert preparing.json()["status"] == "preparing"
        assert ready.json()["status"] == "ready"

    app.dependency_overrides.clear()


def test_invalid_status_transition_returns_409():
    client, SessionLocal = make_client()
    client_id, bouquet_id = seed_data(SessionLocal)

    with client:
        order_id = create_order(client, client_id, bouquet_id).json()["id"]
        response = client.patch(
            f"/api/orders/{order_id}/status",
            json={"status": "ready"},
        )

        assert response.status_code == 409

    app.dependency_overrides.clear()


def test_create_order_with_missing_bouquet_returns_404():
    client, SessionLocal = make_client()
    client_id, _ = seed_data(SessionLocal)

    with client:
        response = create_order(client, client_id, 9999)

        assert response.status_code == 404
        assert response.json() == {"detail": "Bouquet #9999 not found"}

    app.dependency_overrides.clear()


def test_courier_order_without_address_returns_400():
    client, SessionLocal = make_client()
    client_id, bouquet_id = seed_data(SessionLocal)

    with client:
        response = create_order(
            client,
            client_id,
            bouquet_id,
            delivery_type="courier",
        )

        assert response.status_code == 400
        assert "Delivery address is required" in response.json()["detail"]

    app.dependency_overrides.clear()


def test_missing_order_returns_404():
    client, SessionLocal = make_client()
    seed_data(SessionLocal)

    with client:
        response = client.get("/api/orders/9999")

        assert response.status_code == 404
        assert "#9999" in response.json()["detail"]

    app.dependency_overrides.clear()
