from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.notification import Notification, NotificationType


class NotificationRepository:
    """Data-access layer for persisted client notifications."""

    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        client_id: int,
        notification_type: NotificationType,
        message: str,
    ) -> Notification:
        """Create and persist a notification for one client."""
        cleaned_message = message.strip()
        if not cleaned_message:
            raise ValueError("Notification message cannot be empty")

        notification = Notification(
            client_id=client_id,
            type=notification_type,
            message=cleaned_message,
        )
        self.db.add(notification)
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def get_by_id(self, notification_id: int) -> Notification | None:
        return self.db.get(Notification, notification_id)

    def list_for_client(
        self,
        client_id: int,
        *,
        unread_only: bool = False,
    ) -> list[Notification]:
        """Return a client's notifications, newest first."""
        statement = select(Notification).where(Notification.client_id == client_id)
        if unread_only:
            statement = statement.where(Notification.is_read.is_(False))
        statement = statement.order_by(Notification.created_at.desc(), Notification.id.desc())
        return list(self.db.scalars(statement).all())

    def mark_as_read(self, notification_id: int) -> Notification | None:
        notification = self.db.get(Notification, notification_id)
        if notification is None:
            return None

        notification.is_read = True
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def mark_all_as_read(self, client_id: int) -> int:
        """Mark all unread notifications of a client as read and return their count."""
        notifications = self.list_for_client(client_id, unread_only=True)
        for notification in notifications:
            notification.is_read = True

        if notifications:
            self.db.commit()
        return len(notifications)
