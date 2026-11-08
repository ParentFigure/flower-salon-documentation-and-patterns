import os

os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///:memory:")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models import Client, NotificationType, User, UserRole
from app.repositories.notification_repository import NotificationRepository


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


def seed_client(TestingSessionLocal, email: str = "notification-api@example.com") -> int:
    with TestingSessionLocal() as db:
        user = User(
            email=email,
            password_hash="hashed-password",
            role=UserRole.CLIENT,
        )
        client = Client(user=user, full_name="Notification API Client")
        db.add(client)
        db.commit()
        return client.id


def seed_notifications(TestingSessionLocal, client_id: int) -> list[int]:
    with TestingSessionLocal() as db:
        repository = NotificationRepository(db)
        first = repository.create(client_id, NotificationType.NEW_ARRIVAL, "New roses arrived.")
        second = repository.create(client_id, NotificationType.ORDER_READY, "Order #10 is ready.")
        return [first.id, second.id]


def test_list_client_notifications_returns_newest_first():
    client, SessionLocal = make_client()
    client_id = seed_client(SessionLocal)
    notification_ids = seed_notifications(SessionLocal, client_id)

    with client:
        response = client.get(f"/api/notifications/client/{client_id}")
        assert response.status_code == 200
        data = response.json()
        assert [item["id"] for item in data] == list(reversed(notification_ids))
        assert all(item["client_id"] == client_id for item in data)

    app.dependency_overrides.clear()


def test_list_unread_only_filters_read_notifications():
    client, SessionLocal = make_client()
    client_id = seed_client(SessionLocal)
    first_id, second_id = seed_notifications(SessionLocal, client_id)

    with SessionLocal() as db:
        NotificationRepository(db).mark_as_read(first_id)

    with client:
        response = client.get(
            f"/api/notifications/client/{client_id}",
            params={"unread_only": "true"},
        )
        assert response.status_code == 200
        assert [item["id"] for item in response.json()] == [second_id]

    app.dependency_overrides.clear()


def test_list_notifications_for_missing_client_returns_404():
    client, _ = make_client()

    with client:
        response = client.get("/api/notifications/client/9999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Client #9999 not found"

    app.dependency_overrides.clear()


def test_mark_notification_as_read():
    client, SessionLocal = make_client()
    client_id = seed_client(SessionLocal)
    first_id, _ = seed_notifications(SessionLocal, client_id)

    with client:
        response = client.patch(f"/api/notifications/{first_id}/read")
        assert response.status_code == 200
        assert response.json()["id"] == first_id
        assert response.json()["is_read"] is True

    app.dependency_overrides.clear()


def test_mark_missing_notification_as_read_returns_404():
    client, _ = make_client()

    with client:
        response = client.patch("/api/notifications/9999/read")
        assert response.status_code == 404
        assert response.json()["detail"] == "Notification #9999 not found"

    app.dependency_overrides.clear()


def test_mark_all_as_read_returns_changed_count_and_clears_unread():
    client, SessionLocal = make_client()
    client_id = seed_client(SessionLocal)
    seed_notifications(SessionLocal, client_id)

    with client:
        marked = client.patch(f"/api/notifications/client/{client_id}/read-all")
        unread = client.get(
            f"/api/notifications/client/{client_id}",
            params={"unread_only": "true"},
        )

        assert marked.status_code == 200
        assert marked.json() == {"client_id": client_id, "marked_as_read": 2}
        assert unread.status_code == 200
        assert unread.json() == []

    app.dependency_overrides.clear()


def test_mark_all_for_missing_client_returns_404():
    client, _ = make_client()

    with client:
        response = client.patch("/api/notifications/client/9999/read-all")
        assert response.status_code == 404

    app.dependency_overrides.clear()
