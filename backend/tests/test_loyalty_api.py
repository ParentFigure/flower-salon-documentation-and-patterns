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
from app.models import Client, User, UserRole


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


def seed_client(TestingSessionLocal, email: str = "loyalty-api@example.com") -> int:
    with TestingSessionLocal() as db:
        user = User(
            email=email,
            password_hash="hashed-password",
            role=UserRole.CLIENT,
        )
        client = Client(
            user=user,
            full_name="Loyalty API Client",
            phone="+380000000030",
        )
        db.add(client)
        db.commit()
        return client.id


def issue_card(client: TestClient, client_id: int, card_type: str = "bonus"):
    return client.post(
        "/api/loyalty/cards",
        json={"client_id": client_id, "card_type": card_type},
    )


def test_issue_gold_card_returns_201_and_benefits():
    client, SessionLocal = make_client()
    client_id = seed_client(SessionLocal)

    with client:
        response = issue_card(client, client_id, "gold")

        assert response.status_code == 201
        data = response.json()
        assert data["client_id"] == client_id
        assert data["card_type"] == "gold"
        assert Decimal(str(data["discount_percent"])) == Decimal("10.00")
        assert data["free_delivery"] is True

    app.dependency_overrides.clear()


def test_issue_card_for_missing_client_returns_404():
    client, _ = make_client()

    with client:
        response = issue_card(client, 9999)
        assert response.status_code == 404
        assert "Client #9999" in response.json()["detail"]

    app.dependency_overrides.clear()


def test_duplicate_card_returns_409():
    client, SessionLocal = make_client()
    client_id = seed_client(SessionLocal)

    with client:
        assert issue_card(client, client_id).status_code == 201
        response = issue_card(client, client_id, "social")

        assert response.status_code == 409
        assert "already has a loyalty card" in response.json()["detail"]

    app.dependency_overrides.clear()


def test_get_card_returns_existing_card():
    client, SessionLocal = make_client()
    client_id = seed_client(SessionLocal)

    with client:
        created = issue_card(client, client_id, "social").json()
        response = client.get(f"/api/loyalty/clients/{client_id}/card")

        assert response.status_code == 200
        assert response.json()["id"] == created["id"]
        assert response.json()["card_type"] == "social"
        assert Decimal(str(response.json()["discount_percent"])) == Decimal("15.00")

    app.dependency_overrides.clear()


def test_get_missing_card_returns_404():
    client, SessionLocal = make_client()
    client_id = seed_client(SessionLocal)

    with client:
        response = client.get(f"/api/loyalty/clients/{client_id}/card")
        assert response.status_code == 404

    app.dependency_overrides.clear()


def test_accrue_bonus_updates_balance_and_balance_endpoint():
    client, SessionLocal = make_client()
    client_id = seed_client(SessionLocal)

    with client:
        issue_card(client, client_id)
        accrued = client.post(
            f"/api/loyalty/clients/{client_id}/bonus/accrue",
            json={"amount": "250.50"},
        )
        balance = client.get(f"/api/loyalty/clients/{client_id}/balance")

        assert accrued.status_code == 200
        assert Decimal(str(accrued.json()["bonus_balance"])) == Decimal("250.50")
        assert balance.status_code == 200
        assert Decimal(str(balance.json()["bonus_balance"])) == Decimal("250.50")

    app.dependency_overrides.clear()


def test_spend_bonus_updates_balance():
    client, SessionLocal = make_client()
    client_id = seed_client(SessionLocal)

    with client:
        issue_card(client, client_id)
        client.post(
            f"/api/loyalty/clients/{client_id}/bonus/accrue",
            json={"amount": "300.00"},
        )
        response = client.post(
            f"/api/loyalty/clients/{client_id}/bonus/spend",
            json={"amount": "125.00"},
        )

        assert response.status_code == 200
        assert Decimal(str(response.json()["bonus_balance"])) == Decimal("175.00")

    app.dependency_overrides.clear()


def test_spend_more_bonuses_than_available_returns_400():
    client, SessionLocal = make_client()
    client_id = seed_client(SessionLocal)

    with client:
        issue_card(client, client_id)
        response = client.post(
            f"/api/loyalty/clients/{client_id}/bonus/spend",
            json={"amount": "10.00"},
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Not enough bonuses"

    app.dependency_overrides.clear()
