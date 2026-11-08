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
from app.models import User, UserRole


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
            email=f"flower-{role.value}-{suffix}@example.com",
            password_hash="hashed-password",
            role=role,
        )
        db.add(user)
        db.commit()
        token = create_access_token(user.id, role.value)
        return {"Authorization": f"Bearer {token}"}


def create_flower(client: TestClient, headers: dict[str, str], name: str = "Rose"):
    return client.post(
        "/api/flowers",
        headers=headers,
        json={"name": name, "unit_price": "55.50", "stock_qty": 120},
    )


def test_admin_can_create_flower():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        response = create_flower(client, headers)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Rose"
        assert Decimal(str(data["unit_price"])) == Decimal("55.50")
        assert data["stock_qty"] == 120

    app.dependency_overrides.clear()


def test_flower_list_and_detail_are_public():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        flower = create_flower(client, headers, "Tulip").json()

        list_response = client.get("/api/flowers")
        detail_response = client.get(f"/api/flowers/{flower['id']}")

        assert list_response.status_code == 200
        assert [item["name"] for item in list_response.json()] == ["Tulip"]
        assert detail_response.status_code == 200
        assert detail_response.json()["name"] == "Tulip"

    app.dependency_overrides.clear()


def test_missing_flower_returns_404():
    client, _ = make_client()

    with client:
        response = client.get("/api/flowers/999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Flower not found"

    app.dependency_overrides.clear()


def test_create_flower_requires_admin():
    client, SessionLocal = make_client()
    client_headers = auth_headers(SessionLocal, UserRole.CLIENT)

    with client:
        unauthenticated = client.post(
            "/api/flowers",
            json={"name": "Lily", "unit_price": "70.00", "stock_qty": 10},
        )
        forbidden = client.post(
            "/api/flowers",
            headers=client_headers,
            json={"name": "Lily", "unit_price": "70.00", "stock_qty": 10},
        )

        assert unauthenticated.status_code == 401
        assert forbidden.status_code == 403

    app.dependency_overrides.clear()


def test_duplicate_flower_name_returns_409():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        assert create_flower(client, headers, "Peony").status_code == 201
        response = create_flower(client, headers, "Peony")
        assert response.status_code == 409
        assert response.json()["detail"] == "Flower with this name already exists"

    app.dependency_overrides.clear()


def test_admin_can_update_flower():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        flower = create_flower(client, headers, "Daisy").json()
        response = client.put(
            f"/api/flowers/{flower['id']}",
            headers=headers,
            json={"name": "White Daisy", "unit_price": "45.00", "stock_qty": 80},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "White Daisy"
        assert data["stock_qty"] == 80
        assert Decimal(str(data["unit_price"])) == Decimal("45.00")

    app.dependency_overrides.clear()


def test_update_flower_rejects_duplicate_name():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        create_flower(client, headers, "Rose")
        tulip = create_flower(client, headers, "Tulip").json()

        response = client.put(
            f"/api/flowers/{tulip['id']}",
            headers=headers,
            json={"name": "Rose", "unit_price": "60.00", "stock_qty": 10},
        )
        assert response.status_code == 409

    app.dependency_overrides.clear()


def test_admin_can_delete_flower():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        flower = create_flower(client, headers, "Orchid").json()
        response = client.delete(f"/api/flowers/{flower['id']}", headers=headers)

        assert response.status_code == 204
        assert client.get(f"/api/flowers/{flower['id']}").status_code == 404

    app.dependency_overrides.clear()


def test_flower_validation_rejects_negative_stock_and_price():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        response = client.post(
            "/api/flowers",
            headers=headers,
            json={"name": "Bad Flower", "unit_price": "-1.00", "stock_qty": -5},
        )
        assert response.status_code == 422

    app.dependency_overrides.clear()
