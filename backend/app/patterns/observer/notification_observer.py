from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum


class NotificationType(StrEnum):
    """Supported business events that can produce client notifications."""

    ORDER_READY = "order_ready"
    BONUS_ACCRUED = "bonus_accrued"
    NEW_ARRIVAL = "new_arrival"


@dataclass(frozen=True, slots=True)
class NotificationEvent:
    """Immutable event sent by a subject to all subscribed observers."""

    type: NotificationType
    message: str

    def __post_init__(self) -> None:
        if not self.message.strip():
            raise ValueError("Notification message cannot be empty")


class NotificationObserver(ABC):
    """Observer interface for receiving notification events."""

    @abstractmethod
    def update(self, event: NotificationEvent) -> None:
        raise NotImplementedError


class NotificationPublisher:
    """Subject in the GoF Observer pattern."""

    def __init__(self) -> None:
        self._observers: list[NotificationObserver] = []

    @property
    def observers(self) -> tuple[NotificationObserver, ...]:
        return tuple(self._observers)

    def subscribe(self, observer: NotificationObserver) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def unsubscribe(self, observer: NotificationObserver) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, event: NotificationEvent) -> None:
        for observer in tuple(self._observers):
            observer.update(event)

    def order_ready(self, order_id: int) -> None:
        if order_id <= 0:
            raise ValueError("Order id must be greater than zero")
        self.notify(
            NotificationEvent(
                NotificationType.ORDER_READY,
                f"Order #{order_id} is ready for pickup or delivery.",
            )
        )

    def bonus_accrued(self, amount: int) -> None:
        if amount <= 0:
            raise ValueError("Bonus amount must be greater than zero")
        self.notify(
            NotificationEvent(
                NotificationType.BONUS_ACCRUED,
                f"{amount} bonus points were added to your loyalty account.",
            )
        )

    def new_arrival(self, bouquet_name: str) -> None:
        if not bouquet_name.strip():
            raise ValueError("Bouquet name cannot be empty")
        self.notify(
            NotificationEvent(
                NotificationType.NEW_ARRIVAL,
                f"New bouquet in the catalog: {bouquet_name.strip()}.",
            )
        )


class ClientNotificationObserver(NotificationObserver):
    """Simple client-side observer that keeps received events in memory."""

    def __init__(self, client_id: int) -> None:
        if client_id <= 0:
            raise ValueError("Client id must be greater than zero")
        self.client_id = client_id
        self._events: list[NotificationEvent] = []

    @property
    def events(self) -> tuple[NotificationEvent, ...]:
        return tuple(self._events)

    def update(self, event: NotificationEvent) -> None:
        self._events.append(event)
