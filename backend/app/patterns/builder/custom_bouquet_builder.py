from __future__ import annotations

from decimal import Decimal

from app.models.bouquet import Bouquet
from app.models.flower import Flower


class CustomBouquetBuilder:
    """GoF Builder for constructing a custom bouquet step by step."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> "CustomBouquetBuilder":
        self._flowers: list[tuple[Flower, int]] = []
        self._packaging_name: str | None = None
        self._packaging_price = Decimal("0.00")
        self._card_text: str | None = None
        self._card_price = Decimal("0.00")
        return self

    def add_flower(self, flower: Flower, quantity: int = 1) -> "CustomBouquetBuilder":
        if quantity <= 0:
            raise ValueError("Flower quantity must be greater than zero")

        self._flowers.append((flower, quantity))
        return self

    def set_packaging(
        self,
        name: str,
        price: Decimal | int | float | str = Decimal("0.00"),
    ) -> "CustomBouquetBuilder":
        if not name.strip():
            raise ValueError("Packaging name cannot be empty")

        packaging_price = Decimal(str(price))
        if packaging_price < 0:
            raise ValueError("Packaging price cannot be negative")

        self._packaging_name = name.strip()
        self._packaging_price = packaging_price
        return self

    def add_greeting_card(
        self,
        text: str,
        price: Decimal | int | float | str = Decimal("0.00"),
    ) -> "CustomBouquetBuilder":
        if not text.strip():
            raise ValueError("Greeting card text cannot be empty")

        card_price = Decimal(str(price))
        if card_price < 0:
            raise ValueError("Greeting card price cannot be negative")

        self._card_text = text.strip()
        self._card_price = card_price
        return self

    def build(self, name: str = "Custom bouquet") -> Bouquet:
        if not self._flowers:
            raise ValueError("A custom bouquet must contain at least one flower")

        flower_total = sum(
            (flower.unit_price * quantity for flower, quantity in self._flowers),
            start=Decimal("0.00"),
        )
        total_price = flower_total + self._packaging_price + self._card_price

        description_parts = [
            "Flowers: "
            + ", ".join(
                f"{flower.name} x{quantity}" for flower, quantity in self._flowers
            )
        ]

        if self._packaging_name:
            description_parts.append(f"Packaging: {self._packaging_name}")

        if self._card_text:
            description_parts.append(f'Card: "{self._card_text}"')

        bouquet = Bouquet(
            name=name,
            description="; ".join(description_parts),
            base_price=total_price,
            is_custom=True,
        )

        self.reset()
        return bouquet
