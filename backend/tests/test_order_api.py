import os
from decimal import Decimal

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
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


def seed_data(TestingSessionLocal, suffix: str = "main") -> tuple[int, int, int]:
    with TestingSessionLocal() as db:
        user = User(
            email=f"api-order-client-{suffix}@example.com",
            password_hash="hashed-password",
            role=UserRole.CLIENT,
        )
        client = Client(user=user, full_name=f"API Client {suffix}", phone="+380000000020")
        bouquet = Bouquet(
            name=f"API Roses {suffix}",
            description="Bouquet for API order tests",
            base_price=Decimal("500.00"),
            is_custom=False,
        )
        db.add_all([client, bouquet])
        db.commit()
        return client.id, bouquet.id, user.id


def seed_second_client(TestingSessionLocal, suffix: str = "second") -> tuple[int, int]:
    with TestingSessionLocal() as db:
        user = User(
            email=f"api-order-client-{suffix}@example.com",
            password_hash="hashed-password",
            role=UserRole.CLIENT,
        )
        client = Client(user=user, full_name=f"API Client {suffix}")
        db.add(client)
        db.commit()
        return client.id, user.id


def seed_admin(TestingSessionLocal) -> int:
    with TestingSessionLocal() as db:
        admin = User(
            email="api-order-admin@example.com",
            password_hash="hashed-password",
            role=UserRole.ADMIN,
        )
        db.add(admin)
        db.commit()
        return admin.id


def headers_for(user_id: int, role: UserRole) -> dict[str, str]:
    token = create_access_token(user_id, role.value)
    return {"Authorization": f"Bearer {token}"}


def create_order(
    client: TestClient,
    client_id: int,
    bouquet_id: int,
    *,
    headers: dict[str, str] | None = None,
    **overrides,
):
    payload = {
        "client_id": client_id,
        "items": [{"bouquet_id": bouquet_id, "quantity": 2}],
        "delivery_type": "pickup",
        "discount_type": "none",
    }
    payload.update(overrides)
    return client.post("/api/orders", json=payload, headers=headers or {})


def test_create_order_returns_201_and_calculated_totals():
    client, SessionLocal = make_client()
    client_id, bouquet_id, user_id = seed_data(SessionLocal)
    headers = headers_for(user_id, UserRole.CLIENT)

    with client:
        response = create_order(
            client,
            client_id,
            bouquet_id,
            headers=headers,
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

    app.dependency_overrides.clear()


def test_get_order_by_id_for_owner():
    client, SessionLocal = make_client()
    client_id, bouquet_id, user_id = seed_data(SessionLocal)
    headers = headers_for(user_id, UserRole.CLIENT)

    with client:
        created = create_order(client, client_id, bouquet_id, headers=headers).json()
        response = client.get(f"/api/orders/{created['id']}", headers=headers)

        assert response.status_code == 200
        assert response.json()["id"] == created["id"]
        assert response.json()["client_id"] == client_id

    app.dependency_overrides.clear()


def test_list_client_orders_returns_only_clients_orders():
    client, SessionLocal = make_client()
    client_id, bouquet_id, user_id = seed_data(SessionLocal)
    headers = headers_for(user_id, UserRole.CLIENT)

    with client:
        create_order(client, client_id, bouquet_id, headers=headers)
        create_order(
            client,
            client_id,
            bouquet_id,
            headers=headers,
            items=[{"bouquet_id": bouquet_id, "quantity": 1}],
        )

        response = client.get(f"/api/orders/client/{client_id}", headers=headers)

        assert response.status_code == 200
        assert len(response.json()) == 2
        assert all(order["client_id"] == client_id for order in response.json())

    app.dependency_overrides.clear()


def test_status_endpoint_uses_state_transitions_for_admin():
    client, SessionLocal = make_client()
    client_id, bouquet_id, user_id = seed_data(SessionLocal)
    admin_id = seed_admin(SessionLocal)
    client_headers = headers_for(user_id, UserRole.CLIENT)
    admin_headers = headers_for(admin_id, UserRole.ADMIN)

    with client:
        order_id = create_order(client, client_id, bouquet_id, headers=client_headers).json()["id"]

        confirmed = client.patch(
            f"/api/orders/{order_id}/status",
            json={"status": "confirmed"},
            headers=admin_headers,
        )
        preparing = client.patch(
            f"/api/orders/{order_id}/status",
            json={"status": "preparing"},
            headers=admin_headers,
        )
        ready = client.patch(
            f"/api/orders/{order_id}/status",
            json={"status": "ready"},
            headers=admin_headers,
        )

        assert confirmed.status_code == 200
        assert confirmed.json()["status"] == "confirmed"
        assert preparing.json()["status"] == "preparing"
        assert ready.json()["status"] == "ready"

    app.dependency_overrides.clear()


def test_invalid_status_transition_returns_409_for_admin():
    client, SessionLocal = make_client()
    client_id, bouquet_id, user_id = seed_data(SessionLocal)
    admin_id = seed_admin(SessionLocal)

    with client:
        order_id = create_order(
            client,
            client_id,
            bouquet_id,
            headers=headers_for(user_id, UserRole.CLIENT),
        ).json()["id"]
        response = client.patch(
            f"/api/orders/{order_id}/status",
            json={"status": "ready"},
            headers=headers_for(admin_id, UserRole.ADMIN),
        )

        assert response.status_code == 409

    app.dependency_overrides.clear()


def test_create_order_with_missing_bouquet_returns_404():
    client, SessionLocal = make_client()
    client_id, _, user_id = seed_data(SessionLocal)

    with client:
        response = create_order(
            client,
            client_id,
            9999,
            headers=headers_for(user_id, UserRole.CLIENT),
        )

        assert response.status_code == 404
        assert response.json() == {"detail": "Bouquet #9999 not found"}

    app.dependency_overrides.clear()


def test_courier_order_without_address_returns_400():
    client, SessionLocal = make_client()
    client_id, bouquet_id, user_id = seed_data(SessionLocal)

    with client:
        response = create_order(
            client,
            client_id,
            bouquet_id,
            headers=headers_for(user_id, UserRole.CLIENT),
            delivery_type="courier",
        )

        assert response.status_code == 400
        assert "Delivery address is required" in response.json()["detail"]

    app.dependency_overrides.clear()


def test_missing_order_returns_404_for_authenticated_client():
    client, SessionLocal = make_client()
    _, _, user_id = seed_data(SessionLocal)

    with client:
        response = client.get(
            "/api/orders/9999",
            headers=headers_for(user_id, UserRole.CLIENT),
        )

        assert response.status_code == 404
        assert "#9999" in response.json()["detail"]

    app.dependency_overrides.clear()


def test_create_order_requires_authentication():
    client, SessionLocal = make_client()
    client_id, bouquet_id, _ = seed_data(SessionLocal)

    with client:
        response = create_order(client, client_id, bouquet_id)
        assert response.status_code == 401

    app.dependency_overrides.clear()


def test_client_cannot_create_order_for_another_client():
    client, SessionLocal = make_client()
    client_id, bouquet_id, user_id = seed_data(SessionLocal)
    other_client_id, _ = seed_second_client(SessionLocal)

    with client:
        response = create_order(
            client,
            other_client_id,
            bouquet_id,
            headers=headers_for(user_id, UserRole.CLIENT),
        )
        assert response.status_code == 403

    app.dependency_overrides.clear()


def test_client_cannot_read_another_clients_orders():
    client, SessionLocal = make_client()
    client_id, _, user_id = seed_data(SessionLocal)
    other_client_id, _ = seed_second_client(SessionLocal)

    with client:
        response = client.get(
            f"/api/orders/client/{other_client_id}",
            headers=headers_for(user_id, UserRole.CLIENT),
        )
        assert response.status_code == 403

    app.dependency_overrides.clear()


def test_client_cannot_change_order_status():
    client, SessionLocal = make_client()
    client_id, bouquet_id, user_id = seed_data(SessionLocal)
    client_headers = headers_for(user_id, UserRole.CLIENT)

    with client:
        order_id = create_order(client, client_id, bouquet_id, headers=client_headers).json()["id"]
        response = client.patch(
            f"/api/orders/{order_id}/status",
            json={"status": "confirmed"},
            headers=client_headers,
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Administrator role required"

    app.dependency_overrides.clear()
