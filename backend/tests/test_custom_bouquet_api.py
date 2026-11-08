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
from app.models import Client, Flower, Occasion, Packaging, User, UserRole


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
            email=f"custom-{role.value}@example.com",
            password_hash="hashed-password",
            role=role,
        )
        db.add(user)
        db.flush()
        if role == UserRole.CLIENT:
            db.add(Client(user_id=user.id, full_name="Custom Client"))
        db.commit()
        token = create_access_token(user.id, role.value)
        return {"Authorization": f"Bearer {token}"}


def seed_catalog(SessionLocal):
    with SessionLocal() as db:
        rose = Flower(name="Rose", unit_price=Decimal("50.00"), stock_qty=10)
        tulip = Flower(name="Tulip", unit_price=Decimal("35.00"), stock_qty=10)
        packaging = Packaging(
            name="Gift box",
            description="Box packaging",
            price=Decimal("100.00"),
            is_active=True,
        )
        birthday = Occasion(
            name="Birthday",
            slug="birthday",
            description="Birthday bouquets",
            is_active=True,
        )
        db.add_all([rose, tulip, packaging, birthday])
        db.commit()
        return rose.id, tulip.id, packaging.id, birthday.id


def test_client_can_preview_custom_bouquet_with_builder_price():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.CLIENT)
    rose_id, tulip_id, packaging_id, birthday_id = seed_catalog(SessionLocal)

    with client:
        response = client.post(
            "/api/bouquets/custom",
            headers=headers,
            json={
                "name": "My Birthday Bouquet",
                "flowers": [
                    {"flower_id": rose_id, "quantity": 5},
                    {"flower_id": tulip_id, "quantity": 3},
                ],
                "packaging_id": packaging_id,
                "greeting_card_text": "Happy birthday!",
                "occasion_ids": [birthday_id],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "My Birthday Bouquet"
        assert data["is_custom"] is True
        assert Decimal(str(data["total_price"])) == Decimal("480.00")
        assert data["packaging_name"] == "Gift box"
        assert Decimal(str(data["packaging_price"])) == Decimal("100.00")
        assert Decimal(str(data["greeting_card_price"])) == Decimal("25.00")
        assert data["occasion_ids"] == [birthday_id]
        assert "Rose x5" in data["description"]
        assert "Tulip x3" in data["description"]
        assert data["flowers"][0]["unit_price"] == "50.00"

    app.dependency_overrides.clear()


def test_custom_bouquet_requires_authentication():
    client, SessionLocal = make_client()
    rose_id, _, _, _ = seed_catalog(SessionLocal)

    with client:
        response = client.post(
            "/api/bouquets/custom",
            json={"flowers": [{"flower_id": rose_id, "quantity": 1}]},
        )
        assert response.status_code == 401

    app.dependency_overrides.clear()


def test_custom_bouquet_requires_client_role():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.ADMIN)
    rose_id, _, _, _ = seed_catalog(SessionLocal)

    with client:
        response = client.post(
            "/api/bouquets/custom",
            headers=headers,
            json={"flowers": [{"flower_id": rose_id, "quantity": 1}]},
        )
        assert response.status_code == 403

    app.dependency_overrides.clear()


def test_custom_bouquet_missing_flower_returns_404():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.CLIENT)

    with client:
        response = client.post(
            "/api/bouquets/custom",
            headers=headers,
            json={"flowers": [{"flower_id": 999, "quantity": 1}]},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Flower not found: 999"

    app.dependency_overrides.clear()


def test_custom_bouquet_rejects_duplicate_flower():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.CLIENT)
    rose_id, _, _, _ = seed_catalog(SessionLocal)

    with client:
        response = client.post(
            "/api/bouquets/custom",
            headers=headers,
            json={
                "flowers": [
                    {"flower_id": rose_id, "quantity": 1},
                    {"flower_id": rose_id, "quantity": 2},
                ]
            },
        )
        assert response.status_code == 422
        assert "same flower" in response.json()["detail"]

    app.dependency_overrides.clear()


def test_custom_bouquet_rejects_quantity_above_stock():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.CLIENT)
    rose_id, _, _, _ = seed_catalog(SessionLocal)

    with client:
        response = client.post(
            "/api/bouquets/custom",
            headers=headers,
            json={"flowers": [{"flower_id": rose_id, "quantity": 11}]},
        )
        assert response.status_code == 409
        assert "Not enough Rose in stock" in response.json()["detail"]

    app.dependency_overrides.clear()


def test_custom_bouquet_rejects_inactive_packaging():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.CLIENT)
    rose_id, _, packaging_id, _ = seed_catalog(SessionLocal)
    with SessionLocal() as db:
        packaging = db.get(Packaging, packaging_id)
        packaging.is_active = False
        db.commit()

    with client:
        response = client.post(
            "/api/bouquets/custom",
            headers=headers,
            json={
                "flowers": [{"flower_id": rose_id, "quantity": 1}],
                "packaging_id": packaging_id,
            },
        )
        assert response.status_code == 404
        assert response.json()["detail"] == f"Packaging option not found: {packaging_id}"

    app.dependency_overrides.clear()


def test_custom_bouquet_price_cannot_be_supplied_by_client():
    client, SessionLocal = make_client()
    headers = auth_headers(SessionLocal, UserRole.CLIENT)
    rose_id, _, _, _ = seed_catalog(SessionLocal)

    with client:
        response = client.post(
            "/api/bouquets/custom",
            headers=headers,
            json={
                "flowers": [{"flower_id": rose_id, "quantity": 2}],
                "total_price": "1.00",
            },
        )
        assert response.status_code == 200
        assert Decimal(str(response.json()["total_price"])) == Decimal("100.00")

    app.dependency_overrides.clear()
