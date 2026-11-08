import os
from datetime import datetime, timedelta, timezone
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
from app.models import (
    Client,
    LoyaltyCard,
    LoyaltyCardType,
    Notification,
    NotificationType,
    Order,
    User,
    UserRole,
)


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


def headers_for(user_id: int, role: UserRole) -> dict[str, str]:
    token = create_access_token(user_id, role.value)
    return {"Authorization": f"Bearer {token}"}


def seed_client_dashboard(TestingSessionLocal) -> tuple[int, int]:
    with TestingSessionLocal() as db:
        user = User(
            email="profile-client@example.com",
            password_hash="hashed-password",
            role=UserRole.CLIENT,
        )
        client = Client(
            user=user,
            full_name="Marta Profile",
            phone="+380111111111",
        )
        db.add(client)
        db.flush()

        db.add(
            LoyaltyCard(
                client_id=client.id,
                card_type=LoyaltyCardType.BONUS,
                bonus_balance=Decimal("125.50"),
            )
        )

        base_time = datetime.now(timezone.utc)
        for index in range(7):
            db.add(
                Order(
                    client_id=client.id,
                    delivery_type="pickup",
                    total_price=Decimal(str(100 + index)),
                    created_at=base_time + timedelta(minutes=index),
                    updated_at=base_time + timedelta(minutes=index),
                )
            )

        db.add_all(
            [
                Notification(
                    client_id=client.id,
                    type=NotificationType.NEW_ARRIVAL,
                    message="New bouquet",
                    is_read=False,
                ),
                Notification(
                    client_id=client.id,
                    type=NotificationType.ORDER_READY,
                    message="Order ready",
                    is_read=False,
                ),
                Notification(
                    client_id=client.id,
                    type=NotificationType.BONUS_ACCRUED,
                    message="Bonus added",
                    is_read=True,
                ),
            ]
        )
        db.commit()
        return client.id, user.id


def seed_admin(TestingSessionLocal) -> int:
    with TestingSessionLocal() as db:
        user = User(
            email="profile-admin@example.com",
            password_hash="hashed-password",
            role=UserRole.ADMIN,
        )
        db.add(user)
        db.commit()
        return user.id


def seed_client_user_without_profile(TestingSessionLocal) -> int:
    with TestingSessionLocal() as db:
        user = User(
            email="profile-missing@example.com",
            password_hash="hashed-password",
            role=UserRole.CLIENT,
        )
        db.add(user)
        db.commit()
        return user.id


def test_get_profile_returns_personal_cabinet_summary():
    client, SessionLocal = make_client()
    client_id, user_id = seed_client_dashboard(SessionLocal)

    with client:
        response = client.get(
            "/api/profile",
            headers=headers_for(user_id, UserRole.CLIENT),
        )

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == user_id
        assert data["client_id"] == client_id
        assert data["email"] == "profile-client@example.com"
        assert data["full_name"] == "Marta Profile"
        assert data["phone"] == "+380111111111"
        assert data["loyalty_card"]["card_type"] == "bonus"
        assert data["bonus_balance"] == "125.50"
        assert data["total_orders"] == 7
        assert len(data["recent_orders"]) == 5
        assert data["unread_notifications_count"] == 2
        ids = [order["id"] for order in data["recent_orders"]]
        assert ids == sorted(ids, reverse=True)

    app.dependency_overrides.clear()


def test_update_profile_changes_name_and_phone_and_persists():
    client, SessionLocal = make_client()
    client_id, user_id = seed_client_dashboard(SessionLocal)

    with client:
        response = client.patch(
            "/api/profile",
            json={"full_name": "  Marta Updated  ", "phone": "+380222222222"},
            headers=headers_for(user_id, UserRole.CLIENT),
        )
        assert response.status_code == 200
        assert response.json()["full_name"] == "Marta Updated"
        assert response.json()["phone"] == "+380222222222"

    with SessionLocal() as db:
        persisted = db.get(Client, client_id)
        assert persisted.full_name == "Marta Updated"
        assert persisted.phone == "+380222222222"

    app.dependency_overrides.clear()


def test_update_profile_can_clear_phone():
    client, SessionLocal = make_client()
    _, user_id = seed_client_dashboard(SessionLocal)

    with client:
        response = client.patch(
            "/api/profile",
            json={"phone": None},
            headers=headers_for(user_id, UserRole.CLIENT),
        )
        assert response.status_code == 200
        assert response.json()["phone"] is None

    app.dependency_overrides.clear()


def test_profile_without_loyalty_card_returns_zero_balance():
    client, SessionLocal = make_client()
    with SessionLocal() as db:
        user = User(
            email="profile-no-card@example.com",
            password_hash="hashed-password",
            role=UserRole.CLIENT,
        )
        profile = Client(user=user, full_name="No Card")
        db.add(profile)
        db.commit()
        user_id = user.id

    with client:
        response = client.get(
            "/api/profile",
            headers=headers_for(user_id, UserRole.CLIENT),
        )
        assert response.status_code == 200
        assert response.json()["loyalty_card"] is None
        assert response.json()["bonus_balance"] == "0.00"

    app.dependency_overrides.clear()


def test_profile_requires_authentication():
    client, _ = make_client()
    with client:
        response = client.get("/api/profile")
        assert response.status_code == 401
    app.dependency_overrides.clear()


def test_admin_cannot_use_client_profile_endpoint():
    client, SessionLocal = make_client()
    admin_id = seed_admin(SessionLocal)
    with client:
        response = client.get(
            "/api/profile",
            headers=headers_for(admin_id, UserRole.ADMIN),
        )
        assert response.status_code == 403
    app.dependency_overrides.clear()


def test_missing_client_profile_returns_404():
    client, SessionLocal = make_client()
    user_id = seed_client_user_without_profile(SessionLocal)
    with client:
        response = client.get(
            "/api/profile",
            headers=headers_for(user_id, UserRole.CLIENT),
        )
        assert response.status_code == 404
        assert "was not found" in response.json()["detail"]
    app.dependency_overrides.clear()
