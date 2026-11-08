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


def auth_headers(SessionLocal, role: UserRole, suffix: str = "user") -> dict[str, str]:
    with SessionLocal() as db:
        user = User(
            email=f"delivery-{role.value}-{suffix}@example.com",
            password_hash="hashed-password",
            role=role,
        )
        db.add(user)
        db.commit()
        token = create_access_token(user.id, role.value)
        return {"Authorization": f"Bearer {token}"}


def create_salon(
    client: TestClient,
    headers: dict[str, str],
    *,
    name: str = "Flower Salon Center",
    active: bool = True,
):
    return client.post(
        "/api/salons",
        headers=headers,
        json={
            "name": name,
            "address": "Lviv, Rynok Square 1",
            "phone": "+380670000001",
            "description": "Central branch",
            "is_active": active,
        },
    )


def create_delivery_method(
    client: TestClient,
    headers: dict[str, str],
    *,
    code: str = "courier",
    name: str = "Courier delivery",
    price: str = "120.00",
    requires_address: bool = True,
    active: bool = True,
):
    return client.post(
        "/api/delivery-methods",
        headers=headers,
        json={
            "code": code,
            "name": name,
            "description": f"{name} option",
            "base_price": price,
            "requires_address": requires_address,
            "is_active": active,
        },
    )


def seed_order_customer(SessionLocal) -> tuple[int, int, int]:
    with SessionLocal() as db:
        user = User(
            email="delivery-order-client@example.com",
            password_hash="hashed-password",
            role=UserRole.CLIENT,
        )
        customer = Client(user=user, full_name="Delivery Client")
        bouquet = Bouquet(
            name="Delivery Roses",
            description="Test bouquet",
            base_price=Decimal("500.00"),
            is_custom=False,
        )
        db.add_all([customer, bouquet])
        db.commit()
        return customer.id, bouquet.id, user.id


def test_admin_can_create_salon_and_public_can_read_it():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        created = create_salon(client, headers)
        assert created.status_code == 201
        salon = created.json()

        detail = client.get(f"/api/salons/{salon['id']}")
        assert detail.status_code == 200
        assert detail.json()["address"] == "Lviv, Rynok Square 1"

    app.dependency_overrides.clear()


def test_public_salon_list_contains_only_active_salons():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        create_salon(client, headers, name="Active Salon")
        create_salon(client, headers, name="Closed Salon", active=False)
        response = client.get("/api/salons")
        assert response.status_code == 200
        assert [item["name"] for item in response.json()] == ["Active Salon"]

    app.dependency_overrides.clear()


def test_salon_writes_require_admin_and_duplicate_name_is_409():
    client, SessionLocal = make_client()
    admin_headers = auth_headers(SessionLocal, UserRole.ADMIN, "admin")
    client_headers = auth_headers(SessionLocal, UserRole.CLIENT, "client")

    with client:
        payload = {
            "name": "Network Salon",
            "address": "Lviv, Horodotska 10",
            "phone": None,
            "description": None,
            "is_active": True,
        }
        assert client.post("/api/salons", json=payload).status_code == 401
        assert client.post(
            "/api/salons", headers=client_headers, json=payload
        ).status_code == 403
        assert create_salon(client, admin_headers, name="Network Salon").status_code == 201
        assert create_salon(client, admin_headers, name="Network Salon").status_code == 409

    app.dependency_overrides.clear()


def test_admin_can_update_and_delete_salon():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        salon = create_salon(client, headers).json()
        updated = client.put(
            f"/api/salons/{salon['id']}",
            headers=headers,
            json={
                "name": "Flower Salon North",
                "address": "Lviv, Shevchenka 20",
                "phone": "+380670000002",
                "description": "North branch",
                "is_active": True,
            },
        )
        assert updated.status_code == 200
        assert updated.json()["name"] == "Flower Salon North"

        deleted = client.delete(f"/api/salons/{salon['id']}", headers=headers)
        assert deleted.status_code == 204
        assert client.get(f"/api/salons/{salon['id']}").status_code == 404

    app.dependency_overrides.clear()


def test_admin_can_create_delivery_method_and_public_can_read_it():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        created = create_delivery_method(client, headers)
        assert created.status_code == 201
        method = created.json()
        assert Decimal(str(method["base_price"])) == Decimal("120.00")

        detail = client.get(f"/api/delivery-methods/{method['id']}")
        assert detail.status_code == 200
        assert detail.json()["code"] == "courier"

    app.dependency_overrides.clear()


def test_public_delivery_list_contains_only_active_methods():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        create_delivery_method(client, headers, code="courier", name="Courier")
        create_delivery_method(
            client,
            headers,
            code="old-delivery",
            name="Old delivery",
            active=False,
        )
        response = client.get("/api/delivery-methods")
        assert response.status_code == 200
        assert [item["name"] for item in response.json()] == ["Courier"]

    app.dependency_overrides.clear()


def test_delivery_method_writes_require_admin_and_duplicates_return_409():
    client, SessionLocal = make_client()
    admin_headers = auth_headers(SessionLocal, UserRole.ADMIN, "admin")
    client_headers = auth_headers(SessionLocal, UserRole.CLIENT, "client")

    with client:
        payload = {
            "code": "courier",
            "name": "Courier",
            "description": None,
            "base_price": "100.00",
            "requires_address": True,
            "is_active": True,
        }
        assert client.post("/api/delivery-methods", json=payload).status_code == 401
        assert client.post(
            "/api/delivery-methods", headers=client_headers, json=payload
        ).status_code == 403

        assert create_delivery_method(
            client, admin_headers, code="courier", name="Courier"
        ).status_code == 201
        same_code = create_delivery_method(
            client, admin_headers, code="courier", name="Other courier"
        )
        same_name = create_delivery_method(
            client, admin_headers, code="standard", name="Courier"
        )
        assert same_code.status_code == 409
        assert same_name.status_code == 409

    app.dependency_overrides.clear()


def test_invalid_delivery_method_payload_returns_422():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        bad_code = create_delivery_method(
            client,
            headers,
            code="Bad Code!",
            name="Bad code",
        )
        negative_price = create_delivery_method(
            client,
            headers,
            code="negative",
            name="Negative",
            price="-1.00",
        )
        assert bad_code.status_code == 422
        assert negative_price.status_code == 422

    app.dependency_overrides.clear()


def test_admin_can_update_and_delete_delivery_method():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        method = create_delivery_method(client, headers).json()
        updated = client.put(
            f"/api/delivery-methods/{method['id']}",
            headers=headers,
            json={
                "code": "courier",
                "name": "Standard courier",
                "description": "Updated method",
                "base_price": "135.00",
                "requires_address": True,
                "is_active": True,
            },
        )
        assert updated.status_code == 200
        assert Decimal(str(updated.json()["base_price"])) == Decimal("135.00")

        deleted = client.delete(
            f"/api/delivery-methods/{method['id']}", headers=headers
        )
        assert deleted.status_code == 204
        assert client.get(f"/api/delivery-methods/{method['id']}").status_code == 404

    app.dependency_overrides.clear()


def test_order_can_select_configured_pickup_salon():
    client, SessionLocal = make_client()
    admin_headers = auth_headers(SessionLocal, UserRole.ADMIN)
    client_id, bouquet_id, user_id = seed_order_customer(SessionLocal)
    client_headers = {
        "Authorization": f"Bearer {create_access_token(user_id, UserRole.CLIENT.value)}"
    }

    with client:
        salon = create_salon(client, admin_headers).json()
        method = create_delivery_method(
            client,
            admin_headers,
            code="pickup",
            name="Pickup",
            price="0.00",
            requires_address=False,
        ).json()

        response = client.post(
            "/api/orders",
            headers=client_headers,
            json={
                "client_id": client_id,
                "items": [{"bouquet_id": bouquet_id, "quantity": 1}],
                "delivery_method_id": method["id"],
                "pickup_salon_id": salon["id"],
                "discount_type": "none",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["delivery_method_id"] == method["id"]
        assert data["pickup_salon_id"] == salon["id"]
        assert Decimal(str(data["delivery_cost"])) == Decimal("0.00")

    app.dependency_overrides.clear()


def test_configured_pickup_requires_salon():
    client, SessionLocal = make_client()
    admin_headers = auth_headers(SessionLocal, UserRole.ADMIN)
    client_id, bouquet_id, user_id = seed_order_customer(SessionLocal)
    client_headers = {
        "Authorization": f"Bearer {create_access_token(user_id, UserRole.CLIENT.value)}"
    }

    with client:
        method = create_delivery_method(
            client,
            admin_headers,
            code="pickup",
            name="Pickup",
            price="0.00",
            requires_address=False,
        ).json()
        response = client.post(
            "/api/orders",
            headers=client_headers,
            json={
                "client_id": client_id,
                "items": [{"bouquet_id": bouquet_id, "quantity": 1}],
                "delivery_method_id": method["id"],
                "discount_type": "none",
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Pickup salon is required for pickup"

    app.dependency_overrides.clear()


def test_configured_courier_uses_database_price():
    client, SessionLocal = make_client()
    admin_headers = auth_headers(SessionLocal, UserRole.ADMIN)
    client_id, bouquet_id, user_id = seed_order_customer(SessionLocal)
    client_headers = {
        "Authorization": f"Bearer {create_access_token(user_id, UserRole.CLIENT.value)}"
    }

    with client:
        method = create_delivery_method(
            client,
            admin_headers,
            code="courier",
            name="Courier",
            price="135.00",
            requires_address=True,
        ).json()
        response = client.post(
            "/api/orders",
            headers=client_headers,
            json={
                "client_id": client_id,
                "items": [{"bouquet_id": bouquet_id, "quantity": 1}],
                "delivery_method_id": method["id"],
                "delivery_address": "Lviv, Green Street 5",
                "discount_type": "none",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["delivery_method_id"] == method["id"]
        assert data["pickup_salon_id"] is None
        assert Decimal(str(data["delivery_cost"])) == Decimal("135.00")
        assert Decimal(str(data["total_price"])) == Decimal("635.00")

    app.dependency_overrides.clear()


def test_inactive_delivery_method_cannot_be_selected_for_order():
    client, SessionLocal = make_client()
    admin_headers = auth_headers(SessionLocal, UserRole.ADMIN)
    client_id, bouquet_id, user_id = seed_order_customer(SessionLocal)
    client_headers = {
        "Authorization": f"Bearer {create_access_token(user_id, UserRole.CLIENT.value)}"
    }

    with client:
        method = create_delivery_method(
            client,
            admin_headers,
            code="courier",
            name="Inactive courier",
            active=False,
        ).json()
        response = client.post(
            "/api/orders",
            headers=client_headers,
            json={
                "client_id": client_id,
                "items": [{"bouquet_id": bouquet_id, "quantity": 1}],
                "delivery_method_id": method["id"],
                "delivery_address": "Lviv, Green Street 5",
                "discount_type": "none",
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"] == "Delivery method is inactive"

    app.dependency_overrides.clear()
