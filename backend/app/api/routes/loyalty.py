from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.repositories.loyalty_card_repository import LoyaltyCardRepository
from app.repositories.notification_repository import NotificationRepository
from app.schemas.loyalty import (
    BonusAmount,
    BonusBalanceRead,
    LoyaltyCardIssue,
    LoyaltyCardRead,
)
from app.services.loyalty_service import (
    ClientNotFoundError,
    LoyaltyCardAlreadyExistsError,
    LoyaltyCardNotFoundError,
    LoyaltyService,
)

router = APIRouter(prefix="/loyalty", tags=["loyalty"])


def _service(db: Session) -> LoyaltyService:
    return LoyaltyService(
        LoyaltyCardRepository(db),
        notification_repository=NotificationRepository(db),
    )


def _not_found(exc: LookupError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=str(exc),
    )


@router.post("/cards", response_model=LoyaltyCardRead, status_code=status.HTTP_201_CREATED)
def issue_card(payload: LoyaltyCardIssue, db: Session = Depends(get_db)):
    try:
        return _service(db).issue_card(payload.client_id, payload.card_type)
    except ClientNotFoundError as exc:
        raise _not_found(exc) from exc
    except LoyaltyCardAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/clients/{client_id}/card", response_model=LoyaltyCardRead)
def get_card(client_id: int, db: Session = Depends(get_db)):
    try:
        return _service(db).get_card(client_id)
    except LoyaltyCardNotFoundError as exc:
        raise _not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.get("/clients/{client_id}/balance", response_model=BonusBalanceRead)
def get_bonus_balance(client_id: int, db: Session = Depends(get_db)):
    try:
        card = _service(db).get_card(client_id)
        return BonusBalanceRead(
            client_id=card.client_id,
            bonus_balance=card.bonus_balance,
        )
    except LoyaltyCardNotFoundError as exc:
        raise _not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/clients/{client_id}/bonus/accrue", response_model=LoyaltyCardRead)
def accrue_bonus(
    client_id: int,
    payload: BonusAmount,
    db: Session = Depends(get_db),
):
    try:
        return _service(db).accrue_bonus(client_id, payload.amount)
    except LoyaltyCardNotFoundError as exc:
        raise _not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/clients/{client_id}/bonus/spend", response_model=LoyaltyCardRead)
def spend_bonus(
    client_id: int,
    payload: BonusAmount,
    db: Session = Depends(get_db),
):
    try:
        return _service(db).spend_bonus(client_id, payload.amount)
    except LoyaltyCardNotFoundError as exc:
        raise _not_found(exc) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
