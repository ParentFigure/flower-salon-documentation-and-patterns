from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_HALF_UP

from app.models.bouquet import Bouquet


MONEY_STEP = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_STEP, rounding=ROUND_HALF_UP)


class BouquetComponent(ABC):
    """Common component interface used by the Decorator pattern."""

    @abstractmethod
    def get_description(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def get_price(self) -> Decimal:
        raise NotImplementedError


class BasicBouquet(BouquetComponent):
    """Adapter-like component that exposes a Bouquet through the decorator interface."""

    def __init__(self, bouquet: Bouquet) -> None:
        self.bouquet = bouquet

    def get_description(self) -> str:
        return self.bouquet.description or self.bouquet.name

    def get_price(self) -> Decimal:
        return _money(Decimal(self.bouquet.base_price))


class BouquetDecorator(BouquetComponent, ABC):
    """Base decorator that delegates to another bouquet component."""

    def __init__(self, component: BouquetComponent) -> None:
        self._component = component

    def get_description(self) -> str:
        return self._component.get_description()

    def get_price(self) -> Decimal:
        return self._component.get_price()

    @staticmethod
    def _validate_price(price: Decimal) -> None:
        if price < Decimal("0.00"):
            raise ValueError("Decorator price cannot be negative")


class PackagingDecorator(BouquetDecorator):
    """Adds a selected packaging type and its price to a bouquet."""

    def __init__(
        self,
        component: BouquetComponent,
        packaging_name: str,
        price: Decimal = Decimal("70.00"),
    ) -> None:
        if not packaging_name.strip():
            raise ValueError("Packaging name cannot be empty")
        self._validate_price(price)
        super().__init__(component)
        self.packaging_name = packaging_name.strip()
        self.price = price

    def get_description(self) -> str:
        return f"{super().get_description()}, packaging: {self.packaging_name}"

    def get_price(self) -> Decimal:
        return _money(super().get_price() + self.price)


class RibbonDecorator(BouquetDecorator):
    """Adds a decorative ribbon to a bouquet."""

    def __init__(
        self,
        component: BouquetComponent,
        ribbon_color: str,
        price: Decimal = Decimal("20.00"),
    ) -> None:
        if not ribbon_color.strip():
            raise ValueError("Ribbon color cannot be empty")
        self._validate_price(price)
        super().__init__(component)
        self.ribbon_color = ribbon_color.strip()
        self.price = price

    def get_description(self) -> str:
        return f"{super().get_description()}, {self.ribbon_color} ribbon"

    def get_price(self) -> Decimal:
        return _money(super().get_price() + self.price)


class GreetingCardDecorator(BouquetDecorator):
    """Adds a greeting card with custom text to a bouquet."""

    def __init__(
        self,
        component: BouquetComponent,
        text: str,
        price: Decimal = Decimal("25.00"),
    ) -> None:
        if not text.strip():
            raise ValueError("Greeting card text cannot be empty")
        self._validate_price(price)
        super().__init__(component)
        self.text = text.strip()
        self.price = price

    def get_description(self) -> str:
        return f'{super().get_description()}, card: "{self.text}"'

    def get_price(self) -> Decimal:
        return _money(super().get_price() + self.price)
