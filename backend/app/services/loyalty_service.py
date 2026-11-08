from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.models.loyalty_card import LoyaltyCard, LoyaltyCardType
from app.patterns.observer.notification_observer import (
    NotificationPublisher,
    PersistentNotificationObserver,
)
from app.patterns.strategy.delivery import (
    CourierDelivery,
    DeliveryStrategy,
    ExpressDelivery,
    PickupDelivery,
)
from app.patterns.strategy.discount import (
    BonusDiscount,
    DiscountStrategy,
    GoldDiscount,
    NoDiscount,
    SocialDiscount,
)
from app.repositories.loyalty_card_repository import LoyaltyCardRepository
from app.repositories.notification_repository import NotificationRepository


BONUS_ACCRUAL_RATE = Decimal("0.05")
MONEY_STEP = Decimal("0.01")


class ClientNotFoundError(LookupError):
    """Raised when a loyalty operation targets a missing client."""


class LoyaltyCardNotFoundError(LookupError):
    """Raised when a client does not have a loyalty card."""


class LoyaltyCardAlreadyExistsError(ValueError):
    """Raised when a second loyalty card is requested for the same client."""


class LoyaltyService:
    """Application service for loyalty-card business rules."""

    def __init__(
        self,
        repository: LoyaltyCardRepository,
        notifications: NotificationPublisher | None = None,
        notification_repository: NotificationRepository | None = None,
    ) -> None:
        self.repository = repository
        self.notifications = notifications or NotificationPublisher()
        self.notification_repository = notification_repository

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

    def get_card_optional(self, client_id: int) -> LoyaltyCard | None:
        """Return a client's card or ``None`` when no card has been issued."""
        self._validate_client_id(client_id)
        return self.repository.get_by_client_id(client_id)

    def update_card(
        self,
        client_id: int,
        card_type: LoyaltyCardType,
        *,
        is_active: bool = True,
    ) -> LoyaltyCard:
        """Update the type/active state of an existing loyalty card."""
        card = self.get_card(client_id)
        card.card_type = card_type
        card.is_active = is_active
        return self.repository.save(card)

    def accrue_bonus(self, client_id: int, amount: Decimal) -> LoyaltyCard:
        card = self.get_card(client_id)
        card.add_bonus(amount)
        saved_card = self.repository.save(card)
        self._notify_bonus_accrued(client_id, amount)
        return saved_card

    def spend_bonus(self, client_id: int, amount: Decimal) -> LoyaltyCard:
        card = self.get_card(client_id)
        card.spend_bonus(amount)
        return self.repository.save(card)

    def accrue_order_bonus(
        self,
        client_id: int,
        subtotal: Decimal,
        discount_amount: Decimal = Decimal("0.00"),
    ) -> LoyaltyCard | None:
        """Accrue 5% of the paid merchandise amount after order completion.

        Delivery is intentionally excluded from the reward base. Clients without
        an active loyalty card simply receive no bonus.
        """
        card = self.get_card_optional(client_id)
        if card is None or not card.is_active:
            return None

        reward_base = max(subtotal - discount_amount, Decimal("0.00"))
        amount = (reward_base * BONUS_ACCRUAL_RATE).quantize(
            MONEY_STEP,
            rounding=ROUND_HALF_UP,
        )
        if amount <= Decimal("0.00"):
            return card
        return self.accrue_bonus(client_id, amount)

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

    def automatic_discount_strategy_for(self, client_id: int) -> DiscountStrategy:
        """Select a card discount without requiring the client to claim a card type."""
        card = self.get_card_optional(client_id)
        if card is None or not card.is_active:
            return NoDiscount()
        if card.card_type == LoyaltyCardType.GOLD:
            return GoldDiscount(card.discount_percent)
        if card.card_type == LoyaltyCardType.SOCIAL:
            return SocialDiscount(card.discount_percent)
        return NoDiscount()

    def bonus_discount_strategy_for(
        self,
        client_id: int,
        amount: Decimal,
    ) -> DiscountStrategy:
        """Create a bonus discount only when the client owns enough active bonuses."""
        card = self.get_card(client_id)
        if not card.is_active:
            raise ValueError("Loyalty card is inactive")
        if amount < Decimal("0.00"):
            raise ValueError("Bonuses to use cannot be negative")
        current = card.bonus_balance or Decimal("0.00")
        if amount > current:
            raise ValueError("Not enough bonuses")
        return BonusDiscount(amount)

    def apply_delivery_benefit(
        self,
        client_id: int,
        strategy: DeliveryStrategy,
    ) -> DeliveryStrategy:
        """Apply loyalty delivery benefits to an already selected Strategy.

        Active Gold cards make standard courier delivery free. Pickup is already
        free and express delivery remains paid.
        """
        card = self.get_card_optional(client_id)
        if (
            card is not None
            and card.is_active
            and card.free_delivery
            and strategy.name == "courier"
        ):
            return CourierDelivery(fee=Decimal("0.00"))
        return strategy

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
            fee = (
                Decimal("0.00")
                if card.is_active and card.free_delivery
                else Decimal("100.00")
            )
            return CourierDelivery(fee=fee)
        if normalized_type == "express":
            return ExpressDelivery()

        raise ValueError(f"Unsupported delivery type: {delivery_type}")

    def _notify_bonus_accrued(self, client_id: int, amount: Decimal) -> None:
        persistent_observer = None
        if self.notification_repository is not None:
            persistent_observer = PersistentNotificationObserver(
                client_id,
                self.notification_repository,
            )
            self.notifications.subscribe(persistent_observer)

        try:
            self.notifications.bonus_accrued(amount)
        finally:
            if persistent_observer is not None:
                self.notifications.unsubscribe(persistent_observer)

    @staticmethod
    def _validate_client_id(client_id: int) -> None:
        if client_id <= 0:
            raise ValueError("Client id must be greater than zero")
