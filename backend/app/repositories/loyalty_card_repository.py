from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.loyalty_card import LoyaltyCard


class LoyaltyCardRepository:
    """Persistence operations for client loyalty cards."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def client_exists(self, client_id: int) -> bool:
        return self.session.get(Client, client_id) is not None

    def get_by_client_id(self, client_id: int) -> LoyaltyCard | None:
        statement = select(LoyaltyCard).where(LoyaltyCard.client_id == client_id)
        return self.session.scalar(statement)

    def create(self, card: LoyaltyCard) -> LoyaltyCard:
        self.session.add(card)
        self.session.commit()
        self.session.refresh(card)
        return card

    def save(self, card: LoyaltyCard) -> LoyaltyCard:
        self.session.add(card)
        self.session.commit()
        self.session.refresh(card)
        return card
