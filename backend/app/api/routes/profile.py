from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_client
from app.db.session import get_db
from app.models.user import User
from app.repositories.client_repository import ClientRepository
from app.repositories.loyalty_card_repository import LoyaltyCardRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.order_repository import OrderRepository
from app.schemas.profile import ClientProfileRead, ClientProfileUpdate
from app.services.client_profile_service import (
    ClientProfileNotFoundError,
    ClientProfileService,
    ClientProfileSnapshot,
)

router = APIRouter(prefix="/profile", tags=["profile"])


def _service(db: Session) -> ClientProfileService:
    return ClientProfileService(
        ClientRepository(db),
        LoyaltyCardRepository(db),
        OrderRepository(db),
        NotificationRepository(db),
    )


def _to_response(snapshot: ClientProfileSnapshot) -> ClientProfileRead:
    client = snapshot.client
    card = snapshot.loyalty_card
    bonus_balance = card.bonus_balance if card is not None else Decimal("0.00")

    return ClientProfileRead(
        user_id=client.user_id,
        client_id=client.id,
        email=client.user.email,
        full_name=client.full_name,
        phone=client.phone,
        loyalty_card=card,
        bonus_balance=f"{bonus_balance:.2f}",
        total_orders=snapshot.total_orders,
        recent_orders=snapshot.recent_orders,
        unread_notifications_count=snapshot.unread_notifications_count,
    )


@router.get("", response_model=ClientProfileRead)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_client),
):
    try:
        return _to_response(_service(db).get_for_user(current_user.id))
    except ClientProfileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch("", response_model=ClientProfileRead)
def update_profile(
    payload: ClientProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_client),
):
    try:
        snapshot = _service(db).update_for_user(
            current_user.id,
            full_name=payload.full_name,
            phone=payload.phone,
            phone_was_supplied="phone" in payload.model_fields_set,
        )
        return _to_response(snapshot)
    except ClientProfileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
