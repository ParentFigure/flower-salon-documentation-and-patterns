from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import ensure_client_access, get_current_user
from app.db.session import get_db
from app.models.client import Client
from app.models.user import User
from app.repositories.notification_repository import NotificationRepository
from app.schemas.notification import MarkAllReadResponse, NotificationRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _repository(db: Session) -> NotificationRepository:
    return NotificationRepository(db)


def _ensure_client_exists(db: Session, client_id: int) -> None:
    if db.get(Client, client_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Client #{client_id} not found",
        )


@router.get("/client/{client_id}", response_model=list[NotificationRead])
def list_client_notifications(
    client_id: int,
    unread_only: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_client_access(current_user, client_id)
    _ensure_client_exists(db, client_id)
    return _repository(db).list_for_client(client_id, unread_only=unread_only)


@router.patch("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_as_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    repository = _repository(db)
    notification = repository.get_by_id(notification_id)
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notification #{notification_id} not found",
        )

    ensure_client_access(current_user, notification.client_id)
    return repository.mark_as_read(notification_id)


@router.patch("/client/{client_id}/read-all", response_model=MarkAllReadResponse)
def mark_all_client_notifications_as_read(
    client_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ensure_client_access(current_user, client_id)
    _ensure_client_exists(db, client_id)
    changed = _repository(db).mark_all_as_read(client_id)
    return MarkAllReadResponse(client_id=client_id, marked_as_read=changed)
