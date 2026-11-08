from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.notification import NotificationType


class NotificationRead(BaseModel):
    id: int
    client_id: int
    type: NotificationType
    message: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MarkAllReadResponse(BaseModel):
    client_id: int
    marked_as_read: int
