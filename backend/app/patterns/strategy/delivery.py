from abc import ABC, abstractmethod
from decimal import Decimal


class DeliveryStrategy(ABC):
    """Strategy interface for delivery cost calculation."""

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def calculate_cost(self, subtotal: Decimal) -> Decimal:
        raise NotImplementedError

    @staticmethod
    def _validate_subtotal(subtotal: Decimal) -> None:
        if subtotal < Decimal("0.00"):
            raise ValueError("Order subtotal cannot be negative")


class PickupDelivery(DeliveryStrategy):
    """Customer collects the order from a flower salon."""

    @property
    def name(self) -> str:
        return "pickup"

    def calculate_cost(self, subtotal: Decimal) -> Decimal:
        self._validate_subtotal(subtotal)
        return Decimal("0.00")


class CourierDelivery(DeliveryStrategy):
    """Standard courier delivery with a fixed fee."""

    def __init__(self, fee: Decimal = Decimal("100.00")) -> None:
        if fee < Decimal("0.00"):
            raise ValueError("Delivery fee cannot be negative")
        self.fee = fee

    @property
    def name(self) -> str:
        return "courier"

    def calculate_cost(self, subtotal: Decimal) -> Decimal:
        self._validate_subtotal(subtotal)
        return self.fee


class ExpressDelivery(DeliveryStrategy):
    """Faster delivery with a higher fixed fee."""

    def __init__(self, fee: Decimal = Decimal("200.00")) -> None:
        if fee < Decimal("0.00"):
            raise ValueError("Delivery fee cannot be negative")
        self.fee = fee

    @property
    def name(self) -> str:
        return "express"

    def calculate_cost(self, subtotal: Decimal) -> Decimal:
        self._validate_subtotal(subtotal)
        return self.fee


class DeliveryCostCalculator:
    """Context that delegates delivery calculation to the selected strategy."""

    def __init__(self, strategy: DeliveryStrategy) -> None:
        self._strategy = strategy

    @property
    def strategy(self) -> DeliveryStrategy:
        return self._strategy

    def set_strategy(self, strategy: DeliveryStrategy) -> None:
        self._strategy = strategy

    def calculate(self, subtotal: Decimal) -> Decimal:
        return self._strategy.calculate_cost(subtotal)
