from __future__ import annotations

from decimal import Decimal

from app.models.loyalty_card import LoyaltyCard, LoyaltyCardType
from app.patterns.strategy.delivery import (
    CourierDelivery,
    DeliveryStrategy,
    ExpressDelivery,
    PickupDelivery,
)
from app.patterns.strategy.discount import (
    DiscountStrategy,
    GoldDiscount,
    NoDiscount,
    SocialDiscount,
)
from app.repositories.loyalty_card_repository import LoyaltyCardRepository


class ClientNotFoundError(LookupError):
    """Raised when a loyalty operation targets a missing client."""


class LoyaltyCardNotFoundError(LookupError):
    """Raised when a client does not have a loyalty card."""


class LoyaltyCardAlreadyExistsError(ValueError):
    """Raised when a second loyalty card is requested for the same client."""


class LoyaltyService:
    """Application service for loyalty-card business rules."""

    def __init__(self, repository: LoyaltyCardRepository) -> None:
        self.repository = repository

    def issue_card(
        self,
        client_id: int,
        card_type: LoyaltyCardType = LoyaltyCardType.BONUS,
    ) -> LoyaltyCard:
        self._validate_client_id(client_id)
        if not self.repository.client_exists(client_id):
            raise ClientNotFoundError(f"Client #{client_id} was not found")
        if self.repository.get_by_client_id(client_id) is not None:
            raise LoyaltyCardAlreadyExistsError(
                f"Client #{client_id} already has a loyalty card"
            )

        return self.repository.create(
            LoyaltyCard(client_id=client_id, card_type=card_type)
        )

    def get_card(self, client_id: int) -> LoyaltyCard:
        self._validate_client_id(client_id)
        card = self.repository.get_by_client_id(client_id)
        if card is None:
            raise LoyaltyCardNotFoundError(
                f"Loyalty card for client #{client_id} was not found"
            )
        return card

    def accrue_bonus(self, client_id: int, amount: Decimal) -> LoyaltyCard:
        card = self.get_card(client_id)
        card.add_bonus(amount)
        return self.repository.save(card)

    def spend_bonus(self, client_id: int, amount: Decimal) -> LoyaltyCard:
        card = self.get_card(client_id)
        card.spend_bonus(amount)
        return self.repository.save(card)

    def discount_strategy_for(self, client_id: int) -> DiscountStrategy:
        """Select the discount Strategy associated with the client's card."""
        card = self.get_card(client_id)
        if not card.is_active:
            return NoDiscount()
        if card.card_type == LoyaltyCardType.GOLD:
            return GoldDiscount(card.discount_percent)
        if card.card_type == LoyaltyCardType.SOCIAL:
            return SocialDiscount(card.discount_percent)
        return NoDiscount()

    def delivery_strategy_for(
        self,
        client_id: int,
        delivery_type: str,
    ) -> DeliveryStrategy:
        """Select delivery Strategy and apply the Gold free-delivery benefit."""
        card = self.get_card(client_id)
        normalized_type = delivery_type.strip().lower()

        if normalized_type == "pickup":
            return PickupDelivery()
        if normalized_type == "courier":
            fee = Decimal("0.00") if card.is_active and card.free_delivery else Decimal("100.00")
            return CourierDelivery(fee=fee)
        if normalized_type == "express":
            return ExpressDelivery()

        raise ValueError(f"Unsupported delivery type: {delivery_type}")

    @staticmethod
    def _validate_client_id(client_id: int) -> None:
        if client_id <= 0:
            raise ValueError("Client id must be greater than zero")
