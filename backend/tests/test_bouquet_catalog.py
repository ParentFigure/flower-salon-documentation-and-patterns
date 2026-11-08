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
from app.models import Bouquet, BouquetItem, Flower, Occasion, User, UserRole
from app.repositories.bouquet_repository import BouquetRepository


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


def admin_headers(SessionLocal) -> dict[str, str]:
    with SessionLocal() as db:
        user = User(
            email="catalog-admin@example.com",
            password_hash="hashed-password",
            role=UserRole.ADMIN,
        )
        db.add(user)
        db.commit()
        token = create_access_token(user.id, user.role.value)
        return {"Authorization": f"Bearer {token}"}


def seed_catalog(SessionLocal):
    with SessionLocal() as db:
        rose = Flower(name="Rose", unit_price=Decimal("50.00"), stock_qty=100)
        tulip = Flower(name="Tulip", unit_price=Decimal("35.00"), stock_qty=80)
        birthday = Occasion(
            name="Birthday",
            slug="birthday",
            description="Birthday bouquets",
            is_active=True,
        )
        wedding = Occasion(
            name="Wedding",
            slug="wedding",
            description="Wedding bouquets",
            is_active=True,
        )
        db.add_all([rose, tulip, birthday, wedding])
        db.commit()
        return rose.id, tulip.id, birthday.id, wedding.id


def test_admin_can_create_bouquet_with_occasions_and_composition():
    client, SessionLocal = make_client()
    headers = admin_headers(SessionLocal)
    rose_id, tulip_id, birthday_id, _, = seed_catalog(SessionLocal)

    with client:
        response = client.post(
            "/api/bouquets",
            headers=headers,
            json={
                "name": "Birthday Mix",
                "description": "Roses and tulips",
                "base_price": "650.00",
                "is_custom": False,
                "occasion_ids": [birthday_id],
                "composition": [
                    {"flower_id": rose_id, "quantity": 5},
                    {"flower_id": tulip_id, "quantity": 3},
                ],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert [item["slug"] for item in data["occasions"]] == ["birthday"]
        assert data["composition"] == [
            {"flower_id": rose_id, "flower_name": "Rose", "quantity": 5},
            {"flower_id": tulip_id, "flower_name": "Tulip", "quantity": 3},
        ]

    app.dependency_overrides.clear()


def test_public_catalog_can_filter_bouquets_by_occasion_slug():
    client, SessionLocal = make_client()
    headers = admin_headers(SessionLocal)
    rose_id, _, birthday_id, wedding_id = seed_catalog(SessionLocal)

    with client:
        client.post(
            "/api/bouquets",
            headers=headers,
            json={
                "name": "Birthday Roses",
                "base_price": "900.00",
                "occasion_ids": [birthday_id],
                "composition": [{"flower_id": rose_id, "quantity": 9}],
            },
        )
        client.post(
            "/api/bouquets",
            headers=headers,
            json={
                "name": "Wedding Roses",
                "base_price": "1400.00",
                "occasion_ids": [wedding_id],
                "composition": [{"flower_id": rose_id, "quantity": 15}],
            },
        )

        response = client.get("/api/bouquets?occasion=birthday")

        assert response.status_code == 200
        assert [item["name"] for item in response.json()] == ["Birthday Roses"]

    app.dependency_overrides.clear()


def test_unknown_occasion_filter_returns_empty_list():
    client, _ = make_client()

    with client:
        response = client.get("/api/bouquets?occasion=does-not-exist")
        assert response.status_code == 200
        assert response.json() == []

    app.dependency_overrides.clear()


def test_create_bouquet_returns_404_for_missing_flower():
    client, SessionLocal = make_client()
    headers = admin_headers(SessionLocal)
    _, _, birthday_id, _ = seed_catalog(SessionLocal)

    with client:
        response = client.post(
            "/api/bouquets",
            headers=headers,
            json={
                "name": "Broken Bouquet",
                "base_price": "600.00",
                "occasion_ids": [birthday_id],
                "composition": [{"flower_id": 999, "quantity": 2}],
            },
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Flower not found: 999"

    app.dependency_overrides.clear()


def test_create_bouquet_returns_404_for_missing_occasion():
    client, SessionLocal = make_client()
    headers = admin_headers(SessionLocal)
    rose_id, _, _, _ = seed_catalog(SessionLocal)

    with client:
        response = client.post(
            "/api/bouquets",
            headers=headers,
            json={
                "name": "Broken Occasion",
                "base_price": "600.00",
                "occasion_ids": [999],
                "composition": [{"flower_id": rose_id, "quantity": 2}],
            },
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Occasion not found: 999"

    app.dependency_overrides.clear()


def test_duplicate_flower_in_composition_is_rejected():
    client, SessionLocal = make_client()
    headers = admin_headers(SessionLocal)
    rose_id, _, birthday_id, _ = seed_catalog(SessionLocal)

    with client:
        response = client.post(
            "/api/bouquets",
            headers=headers,
            json={
                "name": "Duplicate Rose",
                "base_price": "600.00",
                "occasion_ids": [birthday_id],
                "composition": [
                    {"flower_id": rose_id, "quantity": 2},
                    {"flower_id": rose_id, "quantity": 3},
                ],
            },
        )
        assert response.status_code == 422
        assert "same flower" in response.json()["detail"]

    app.dependency_overrides.clear()


def test_repository_can_replace_bouquet_composition_and_occasions():
    _, SessionLocal = make_client()
    rose_id, tulip_id, birthday_id, wedding_id = seed_catalog(SessionLocal)

    with SessionLocal() as db:
        repository = BouquetRepository(db)
        bouquet = repository.create(
            Bouquet(name="Editable", base_price=Decimal("500.00"), is_custom=False)
        )
        repository.set_occasions(bouquet, [birthday_id])
        repository.set_composition(bouquet, [(rose_id, 4)])

        repository.set_occasions(bouquet, [wedding_id])
        updated = repository.set_composition(bouquet, [(tulip_id, 7)])

        assert [occasion.slug for occasion in updated.occasions] == ["wedding"]
        assert len(updated.items) == 1
        assert isinstance(updated.items[0], BouquetItem)
        assert updated.items[0].flower.name == "Tulip"
        assert updated.items[0].quantity == 7

    app.dependency_overrides.clear()
