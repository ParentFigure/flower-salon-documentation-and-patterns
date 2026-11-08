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


def seed_client(TestingSessionLocal, email: str = "loyalty-api@example.com") -> tuple[int, int]:
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
        return client.id, user.id


def seed_admin(TestingSessionLocal) -> int:
    with TestingSessionLocal() as db:
        admin = User(
            email="loyalty-admin@example.com",
            password_hash="hashed-password",
            role=UserRole.ADMIN,
        )
        db.add(admin)
        db.commit()
        return admin.id


def headers_for(user_id: int, role: UserRole) -> dict[str, str]:
    token = create_access_token(user_id, role.value)
    return {"Authorization": f"Bearer {token}"}


def issue_card(
    client: TestClient,
    client_id: int,
    admin_headers: dict[str, str],
    card_type: str = "bonus",
):
    return client.post(
        "/api/loyalty/cards",
        json={"client_id": client_id, "card_type": card_type},
        headers=admin_headers,
    )


def test_issue_gold_card_returns_201_and_benefits_for_admin():
    client, SessionLocal = make_client()
    client_id, _ = seed_client(SessionLocal)
    admin_id = seed_admin(SessionLocal)

    with client:
        response = issue_card(
            client,
            client_id,
            headers_for(admin_id, UserRole.ADMIN),
            "gold",
        )

        assert response.status_code == 201
        data = response.json()
        assert data["client_id"] == client_id
        assert data["card_type"] == "gold"
        assert Decimal(str(data["discount_percent"])) == Decimal("10.00")
        assert data["free_delivery"] is True

    app.dependency_overrides.clear()


def test_issue_card_for_missing_client_returns_404_for_admin():
    client, SessionLocal = make_client()
    admin_id = seed_admin(SessionLocal)

    with client:
        response = issue_card(client, 9999, headers_for(admin_id, UserRole.ADMIN))
        assert response.status_code == 404
        assert "Client #9999" in response.json()["detail"]

    app.dependency_overrides.clear()


def test_duplicate_card_returns_409():
    client, SessionLocal = make_client()
    client_id, _ = seed_client(SessionLocal)
    admin_id = seed_admin(SessionLocal)
    admin_headers = headers_for(admin_id, UserRole.ADMIN)

    with client:
        assert issue_card(client, client_id, admin_headers).status_code == 201
        response = issue_card(client, client_id, admin_headers, "social")

        assert response.status_code == 409
        assert "already has a loyalty card" in response.json()["detail"]

    app.dependency_overrides.clear()


def test_get_card_returns_existing_card_for_owner():
    client, SessionLocal = make_client()
    client_id, user_id = seed_client(SessionLocal)
    admin_id = seed_admin(SessionLocal)

    with client:
        created = issue_card(
            client,
            client_id,
            headers_for(admin_id, UserRole.ADMIN),
            "social",
        ).json()
        response = client.get(
            f"/api/loyalty/clients/{client_id}/card",
            headers=headers_for(user_id, UserRole.CLIENT),
        )

        assert response.status_code == 200
        assert response.json()["id"] == created["id"]
        assert response.json()["card_type"] == "social"
        assert Decimal(str(response.json()["discount_percent"])) == Decimal("15.00")

    app.dependency_overrides.clear()


def test_get_missing_card_returns_404_for_owner():
    client, SessionLocal = make_client()
    client_id, user_id = seed_client(SessionLocal)

    with client:
        response = client.get(
            f"/api/loyalty/clients/{client_id}/card",
            headers=headers_for(user_id, UserRole.CLIENT),
        )
        assert response.status_code == 404

    app.dependency_overrides.clear()


def test_accrue_bonus_updates_balance_and_balance_endpoint():
    client, SessionLocal = make_client()
    client_id, user_id = seed_client(SessionLocal)
    admin_id = seed_admin(SessionLocal)
    admin_headers = headers_for(admin_id, UserRole.ADMIN)

    with client:
        issue_card(client, client_id, admin_headers)
        accrued = client.post(
            f"/api/loyalty/clients/{client_id}/bonus/accrue",
            json={"amount": "250.50"},
            headers=admin_headers,
        )
        balance = client.get(
            f"/api/loyalty/clients/{client_id}/balance",
            headers=headers_for(user_id, UserRole.CLIENT),
        )

        assert accrued.status_code == 200
        assert Decimal(str(accrued.json()["bonus_balance"])) == Decimal("250.50")
        assert balance.status_code == 200
        assert Decimal(str(balance.json()["bonus_balance"])) == Decimal("250.50")

    app.dependency_overrides.clear()


def test_spend_bonus_updates_balance_for_owner():
    client, SessionLocal = make_client()
    client_id, user_id = seed_client(SessionLocal)
    admin_id = seed_admin(SessionLocal)
    admin_headers = headers_for(admin_id, UserRole.ADMIN)

    with client:
        issue_card(client, client_id, admin_headers)
        client.post(
            f"/api/loyalty/clients/{client_id}/bonus/accrue",
            json={"amount": "300.00"},
            headers=admin_headers,
        )
        response = client.post(
            f"/api/loyalty/clients/{client_id}/bonus/spend",
            json={"amount": "125.00"},
            headers=headers_for(user_id, UserRole.CLIENT),
        )

        assert response.status_code == 200
        assert Decimal(str(response.json()["bonus_balance"])) == Decimal("175.00")

    app.dependency_overrides.clear()


def test_spend_more_bonuses_than_available_returns_400():
    client, SessionLocal = make_client()
    client_id, user_id = seed_client(SessionLocal)
    admin_id = seed_admin(SessionLocal)

    with client:
        issue_card(client, client_id, headers_for(admin_id, UserRole.ADMIN))
        response = client.post(
            f"/api/loyalty/clients/{client_id}/bonus/spend",
            json={"amount": "10.00"},
            headers=headers_for(user_id, UserRole.CLIENT),
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Not enough bonuses"

    app.dependency_overrides.clear()


def test_client_cannot_issue_loyalty_card():
    client, SessionLocal = make_client()
    client_id, user_id = seed_client(SessionLocal)

    with client:
        response = client.post(
            "/api/loyalty/cards",
            json={"client_id": client_id, "card_type": "bonus"},
            headers=headers_for(user_id, UserRole.CLIENT),
        )
        assert response.status_code == 403

    app.dependency_overrides.clear()


def test_client_cannot_read_another_clients_card():
    client, SessionLocal = make_client()
    first_client_id, first_user_id = seed_client(SessionLocal, "first-loyalty@example.com")
    second_client_id, _ = seed_client(SessionLocal, "second-loyalty@example.com")

    with client:
        response = client.get(
            f"/api/loyalty/clients/{second_client_id}/card",
            headers=headers_for(first_user_id, UserRole.CLIENT),
        )
        assert response.status_code == 403

    app.dependency_overrides.clear()


def test_client_cannot_accrue_bonus_manually():
    client, SessionLocal = make_client()
    client_id, user_id = seed_client(SessionLocal)

    with client:
        response = client.post(
            f"/api/loyalty/clients/{client_id}/bonus/accrue",
            json={"amount": "50.00"},
            headers=headers_for(user_id, UserRole.CLIENT),
        )
        assert response.status_code == 403

    app.dependency_overrides.clear()


def test_loyalty_card_read_requires_authentication():
    client, SessionLocal = make_client()
    client_id, _ = seed_client(SessionLocal)

    with client:
        response = client.get(f"/api/loyalty/clients/{client_id}/card")
        assert response.status_code == 401

    app.dependency_overrides.clear()
