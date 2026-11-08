from __future__ import annotations

from dataclasses import dataclass

from app.models.client import Client
from app.models.loyalty_card import LoyaltyCard
from app.models.order import Order
from app.repositories.client_repository import ClientRepository
from app.repositories.loyalty_card_repository import LoyaltyCardRepository
from app.repositories.notification_repository import NotificationRepository
from app.repositories.order_repository import OrderRepository


class ClientProfileNotFoundError(LookupError):
    """Raised when an authenticated client account has no client profile."""


@dataclass(slots=True)
class ClientProfileSnapshot:
    client: Client
    loyalty_card: LoyaltyCard | None
    recent_orders: list[Order]
    total_orders: int
    unread_notifications_count: int


class ClientProfileService:
    """Application service that aggregates personal-cabinet data."""

    RECENT_ORDERS_LIMIT = 5

    def __init__(
        self,
        client_repository: ClientRepository,
        loyalty_repository: LoyaltyCardRepository,
        order_repository: OrderRepository,
        notification_repository: NotificationRepository,
    ) -> None:
        self.client_repository = client_repository
        self.loyalty_repository = loyalty_repository
        self.order_repository = order_repository
        self.notification_repository = notification_repository

    def get_for_user(self, user_id: int) -> ClientProfileSnapshot:
        client = self.client_repository.get_by_user_id(user_id)
        if client is None:
            raise ClientProfileNotFoundError(
                f"Client profile for user #{user_id} was not found"
            )

        orders = self.order_repository.list_for_client(client.id)
        unread = self.notification_repository.list_for_client(
            client.id,
            unread_only=True,
        )
        card = self.loyalty_repository.get_by_client_id(client.id)

        return ClientProfileSnapshot(
            client=client,
            loyalty_card=card,
            recent_orders=orders[: self.RECENT_ORDERS_LIMIT],
            total_orders=len(orders),
            unread_notifications_count=len(unread),
        )

    def update_for_user(
        self,
        user_id: int,
        *,
        full_name: str | None = None,
        phone: str | None = None,
        phone_was_supplied: bool = False,
    ) -> ClientProfileSnapshot:
        client = self.client_repository.get_by_user_id(user_id)
        if client is None:
            raise ClientProfileNotFoundError(
                f"Client profile for user #{user_id} was not found"
            )

        if full_name is not None:
            cleaned_name = full_name.strip()
            if not cleaned_name:
                raise ValueError("Full name cannot be empty")
            client.full_name = cleaned_name

        if phone_was_supplied:
            cleaned_phone = phone.strip() if phone is not None else None
            client.phone = cleaned_phone or None

        self.client_repository.save(client)
        return self.get_for_user(user_id)
