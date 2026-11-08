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


def auth_headers(SessionLocal, role: UserRole) -> dict[str, str]:
    with SessionLocal() as db:
        user = User(
            email=f"bouquet-{role.value}@example.com",
            password_hash="hashed-password",
            role=role,
        )
        db.add(user)
        db.commit()
        token = create_access_token(user.id, role.value)
        return {"Authorization": f"Bearer {token}"}


def test_create_bouquet_returns_201_and_saved_bouquet():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        response = client.post(
            "/api/bouquets",
            headers=headers,
            json={
                "name": "Birthday Roses",
                "description": "Red roses for a birthday",
                "base_price": "1250.00",
                "is_custom": False,
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 1
        assert data["name"] == "Birthday Roses"
        assert Decimal(str(data["base_price"])) == Decimal("1250.00")

    app.dependency_overrides.clear()


def test_list_bouquets_is_public_and_returns_created_items():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        client.post(
            "/api/bouquets",
            headers=headers,
            json={"name": "Rose Classic", "base_price": "1200.00", "is_custom": False},
        )
        client.post(
            "/api/bouquets",
            headers=headers,
            json={"name": "Custom Mix", "base_price": "950.00", "is_custom": True},
        )

        response = client.get("/api/bouquets")

        assert response.status_code == 200
        assert [item["name"] for item in response.json()] == ["Rose Classic", "Custom Mix"]

    app.dependency_overrides.clear()


def test_get_bouquet_by_id_is_public():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        created = client.post(
            "/api/bouquets",
            headers=headers,
            json={"name": "Wedding White", "base_price": "1800.00", "is_custom": False},
        ).json()

        response = client.get(f"/api/bouquets/{created['id']}")

        assert response.status_code == 200
        assert response.json()["name"] == "Wedding White"

    app.dependency_overrides.clear()


def test_get_missing_bouquet_returns_404_without_auth():
    client, _ = make_client()

    with client:
        response = client.get("/api/bouquets/999")

        assert response.status_code == 404
        assert response.json() == {"detail": "Bouquet not found"}

    app.dependency_overrides.clear()


def test_create_bouquet_rejects_non_positive_price_for_admin():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)

    with client:
        response = client.post(
            "/api/bouquets",
            headers=headers,
            json={"name": "Invalid Bouquet", "base_price": "0.00", "is_custom": False},
        )

        assert response.status_code == 422

    app.dependency_overrides.clear()


def test_create_bouquet_requires_authentication():
    client, _ = make_client()

    with client:
        response = client.post(
            "/api/bouquets",
            json={"name": "Protected", "base_price": "500.00", "is_custom": False},
        )
        assert response.status_code == 401

    app.dependency_overrides.clear()


def test_client_cannot_create_bouquet():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.CLIENT)

    with client:
        response = client.post(
            "/api/bouquets",
            headers=headers,
            json={"name": "Forbidden", "base_price": "500.00", "is_custom": False},
        )
        assert response.status_code == 403
        assert response.json()["detail"] == "Administrator role required"

    app.dependency_overrides.clear()
