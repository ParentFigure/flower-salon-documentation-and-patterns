from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_HALF_UP


MONEY_STEP = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_STEP, rounding=ROUND_HALF_UP)


class DiscountStrategy(ABC):
    """Strategy interface for calculating the final price after a discount."""

    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def apply(self, subtotal: Decimal) -> Decimal:
        raise NotImplementedError

    @staticmethod
    def _validate_subtotal(subtotal: Decimal) -> None:
        if subtotal < Decimal("0.00"):
            raise ValueError("Order subtotal cannot be negative")


class NoDiscount(DiscountStrategy):
    """Keeps the order price unchanged."""

    @property
    def name(self) -> str:
        return "none"

    def apply(self, subtotal: Decimal) -> Decimal:
        self._validate_subtotal(subtotal)
        return _money(subtotal)


class PercentageDiscount(DiscountStrategy):
    """Base strategy for discounts expressed as a percentage."""

    def __init__(self, percent: Decimal, strategy_name: str = "percentage") -> None:
        if percent < Decimal("0.00") or percent > Decimal("100.00"):
            raise ValueError("Discount percent must be between 0 and 100")
        self.percent = percent
        self._name = strategy_name

    @property
    def name(self) -> str:
        return self._name

    def apply(self, subtotal: Decimal) -> Decimal:
        self._validate_subtotal(subtotal)
        multiplier = Decimal("1.00") - self.percent / Decimal("100.00")
        return _money(subtotal * multiplier)


class GoldDiscount(PercentageDiscount):
    """Configurable discount for Gold loyalty-card holders."""

    def __init__(self, percent: Decimal = Decimal("10.00")) -> None:
        super().__init__(percent=percent, strategy_name="gold")


class SocialDiscount(PercentageDiscount):
    """Configurable discount for customers with a social card."""

    def __init__(self, percent: Decimal = Decimal("15.00")) -> None:
        super().__init__(percent=percent, strategy_name="social")


class EventDiscount(PercentageDiscount):
    """Temporary percentage discount tied to an occasion or campaign."""

    def __init__(
        self,
        event_name: str,
        percent: Decimal = Decimal("10.00"),
    ) -> None:
        if not event_name.strip():
            raise ValueError("Event name cannot be empty")
        self.event_name = event_name.strip()
        super().__init__(percent=percent, strategy_name="event")


class BonusDiscount(DiscountStrategy):
    """Uses a fixed amount of accumulated bonuses, capped by the subtotal."""

    def __init__(self, bonuses_to_use: Decimal) -> None:
        if bonuses_to_use < Decimal("0.00"):
            raise ValueError("Bonuses to use cannot be negative")
        self.bonuses_to_use = bonuses_to_use

    @property
    def name(self) -> str:
        return "bonus"

    def apply(self, subtotal: Decimal) -> Decimal:
        self._validate_subtotal(subtotal)
        discount = min(self.bonuses_to_use, subtotal)
        return _money(subtotal - discount)


class DiscountCalculator:
    """Context that delegates price calculation to the selected strategy."""

    def __init__(self, strategy: DiscountStrategy) -> None:
        self._strategy = strategy

    @property
    def strategy(self) -> DiscountStrategy:
        return self._strategy

    def set_strategy(self, strategy: DiscountStrategy) -> None:
        self._strategy = strategy

    def calculate(self, subtotal: Decimal) -> Decimal:
        return self._strategy.apply(subtotal)
