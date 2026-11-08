from __future__ import annotations

from abc import ABC


class InvalidOrderStateTransition(ValueError):
    """Raised when an operation is not allowed for the current order state."""


class OrderState(ABC):
    """Base state used by the GoF State pattern."""

    name = "unknown"

    def _invalid(self, action: str) -> None:
        raise InvalidOrderStateTransition(
            f"Cannot {action} order while it is in '{self.name}' state"
        )

    def confirm(self, order: "OrderStateContext") -> None:
        self._invalid("confirm")

    def start_preparing(self, order: "OrderStateContext") -> None:
        self._invalid("start preparing")

    def mark_ready(self, order: "OrderStateContext") -> None:
        self._invalid("mark ready")

    def start_delivery(self, order: "OrderStateContext") -> None:
        self._invalid("start delivery")

    def complete(self, order: "OrderStateContext") -> None:
        self._invalid("complete")

    def cancel(self, order: "OrderStateContext") -> None:
        self._invalid("cancel")


class CreatedState(OrderState):
    name = "created"

    def confirm(self, order: "OrderStateContext") -> None:
        order._transition_to(ConfirmedState())

    def cancel(self, order: "OrderStateContext") -> None:
        order._transition_to(CancelledState())


class ConfirmedState(OrderState):
    name = "confirmed"

    def start_preparing(self, order: "OrderStateContext") -> None:
        order._transition_to(PreparingState())

    def cancel(self, order: "OrderStateContext") -> None:
        order._transition_to(CancelledState())


class PreparingState(OrderState):
    name = "preparing"

    def mark_ready(self, order: "OrderStateContext") -> None:
        order._transition_to(ReadyState())


class ReadyState(OrderState):
    name = "ready"

    def start_delivery(self, order: "OrderStateContext") -> None:
        order._transition_to(DeliveringState())


class DeliveringState(OrderState):
    name = "delivering"

    def complete(self, order: "OrderStateContext") -> None:
        order._transition_to(CompletedState())


class CompletedState(OrderState):
    name = "completed"


class CancelledState(OrderState):
    name = "cancelled"


class OrderStateContext:
    """Context that delegates order lifecycle operations to the current state."""

    def __init__(self, state: OrderState | None = None) -> None:
        self._state = state or CreatedState()
        self._history: list[str] = [self._state.name]

    @property
    def state(self) -> OrderState:
        return self._state

    @property
    def status(self) -> str:
        return self._state.name

    @property
    def history(self) -> tuple[str, ...]:
        return tuple(self._history)

    def _transition_to(self, state: OrderState) -> None:
        self._state = state
        self._history.append(state.name)

    def confirm(self) -> None:
        self._state.confirm(self)

    def start_preparing(self) -> None:
        self._state.start_preparing(self)

    def mark_ready(self) -> None:
        self._state.mark_ready(self)

    def start_delivery(self) -> None:
        self._state.start_delivery(self)

    def complete(self) -> None:
        self._state.complete(self)

    def cancel(self) -> None:
        self._state.cancel(self)
