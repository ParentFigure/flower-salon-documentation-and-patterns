import os
from decimal import Decimal

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.bouquet import Bouquet


def make_client() -> TestClient:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine, tables=[Bouquet.__table__])
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_create_bouquet_returns_201_and_saved_bouquet():
    with make_client() as client:
        response = client.post(
            "/api/bouquets",
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


def test_list_bouquets_returns_created_items():
    with make_client() as client:
        client.post(
            "/api/bouquets",
            json={"name": "Rose Classic", "base_price": "1200.00", "is_custom": False},
        )
        client.post(
            "/api/bouquets",
            json={"name": "Custom Mix", "base_price": "950.00", "is_custom": True},
        )

        response = client.get("/api/bouquets")

        assert response.status_code == 200
        assert [item["name"] for item in response.json()] == ["Rose Classic", "Custom Mix"]

    app.dependency_overrides.clear()


def test_get_bouquet_by_id():
    with make_client() as client:
        created = client.post(
            "/api/bouquets",
            json={"name": "Wedding White", "base_price": "1800.00", "is_custom": False},
        ).json()

        response = client.get(f"/api/bouquets/{created['id']}")

        assert response.status_code == 200
        assert response.json()["name"] == "Wedding White"

    app.dependency_overrides.clear()


def test_get_missing_bouquet_returns_404():
    with make_client() as client:
        response = client.get("/api/bouquets/999")

        assert response.status_code == 404
        assert response.json() == {"detail": "Bouquet not found"}

    app.dependency_overrides.clear()


def test_create_bouquet_rejects_non_positive_price():
    with make_client() as client:
        response = client.post(
            "/api/bouquets",
            json={"name": "Invalid Bouquet", "base_price": "0.00", "is_custom": False},
        )

        assert response.status_code == 422

    app.dependency_overrides.clear()
