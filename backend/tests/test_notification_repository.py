from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Client, NotificationType, User, UserRole
from app.repositories.notification_repository import NotificationRepository


def build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def create_client(session: Session) -> Client:
    user = User(
        email="notification-client@example.com",
        password_hash="hashed-password",
        role=UserRole.CLIENT,
    )
    client = Client(user=user, full_name="Notification Client")
    session.add(client)
    session.commit()
    return client


def test_create_persists_unread_notification():
    session = build_session()
    client = create_client(session)
    repository = NotificationRepository(session)

    notification = repository.create(
        client.id,
        NotificationType.ORDER_READY,
        "Order #42 is ready.",
    )

    assert notification.id is not None
    assert notification.client_id == client.id
    assert notification.type == NotificationType.ORDER_READY
    assert notification.message == "Order #42 is ready."
    assert notification.is_read is False
    assert notification.created_at is not None


def test_create_strips_message_and_rejects_empty_message():
    session = build_session()
    client = create_client(session)
    repository = NotificationRepository(session)

    created = repository.create(
        client.id,
        NotificationType.NEW_ARRIVAL,
        "  New bouquet arrived.  ",
    )
    assert created.message == "New bouquet arrived."

    try:
        repository.create(client.id, NotificationType.NEW_ARRIVAL, "   ")
    except ValueError as exc:
        assert str(exc) == "Notification message cannot be empty"
    else:
        raise AssertionError("Expected ValueError for an empty message")


def test_get_by_id_returns_notification_and_none_for_missing():
    session = build_session()
    client = create_client(session)
    repository = NotificationRepository(session)
    created = repository.create(client.id, NotificationType.BONUS_ACCRUED, "100 bonuses added.")

    assert repository.get_by_id(created.id).id == created.id
    assert repository.get_by_id(9999) is None


def test_list_for_client_returns_only_client_notifications_newest_first():
    session = build_session()
    first_client = create_client(session)
    second_user = User(
        email="other-notification-client@example.com",
        password_hash="hashed-password",
        role=UserRole.CLIENT,
    )
    second_client = Client(user=second_user, full_name="Other Client")
    session.add(second_client)
    session.commit()
    repository = NotificationRepository(session)

    first = repository.create(first_client.id, NotificationType.NEW_ARRIVAL, "First")
    second = repository.create(first_client.id, NotificationType.ORDER_READY, "Second")
    repository.create(second_client.id, NotificationType.BONUS_ACCRUED, "Other client")

    result = repository.list_for_client(first_client.id)

    assert [item.id for item in result] == [second.id, first.id]


def test_unread_filter_and_mark_as_read():
    session = build_session()
    client = create_client(session)
    repository = NotificationRepository(session)
    first = repository.create(client.id, NotificationType.NEW_ARRIVAL, "First")
    second = repository.create(client.id, NotificationType.ORDER_READY, "Second")

    updated = repository.mark_as_read(first.id)

    assert updated is not None
    assert updated.is_read is True
    assert [item.id for item in repository.list_for_client(client.id, unread_only=True)] == [second.id]


def test_mark_as_read_returns_none_for_missing_notification():
    session = build_session()
    repository = NotificationRepository(session)

    assert repository.mark_as_read(9999) is None


def test_mark_all_as_read_marks_only_clients_unread_notifications():
    session = build_session()
    client = create_client(session)
    other_user = User(
        email="third-notification-client@example.com",
        password_hash="hashed-password",
        role=UserRole.CLIENT,
    )
    other_client = Client(user=other_user, full_name="Third Client")
    session.add(other_client)
    session.commit()
    repository = NotificationRepository(session)

    repository.create(client.id, NotificationType.NEW_ARRIVAL, "First")
    repository.create(client.id, NotificationType.BONUS_ACCRUED, "Second")
    other = repository.create(other_client.id, NotificationType.ORDER_READY, "Other")

    changed = repository.mark_all_as_read(client.id)

    assert changed == 2
    assert repository.list_for_client(client.id, unread_only=True) == []
    assert repository.get_by_id(other.id).is_read is False
