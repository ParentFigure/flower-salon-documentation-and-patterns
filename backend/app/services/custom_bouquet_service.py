from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.bouquet import Bouquet
from app.models.flower import Flower
from app.models.order_item import OrderItem
from app.patterns.builder import CustomBouquetBuilder
from app.repositories.flower_repository import FlowerRepository
from app.repositories.occasion_repository import OccasionRepository
from app.repositories.packaging_repository import PackagingRepository

GREETING_CARD_PRICE = Decimal("25.00")


class CustomBouquetValidationError(ValueError):
    """Raised when a custom bouquet request violates business rules."""


class CustomBouquetResourceNotFoundError(LookupError):
    """Raised when a flower, packaging option or occasion does not exist."""


class InsufficientFlowerStockError(RuntimeError):
    """Raised when the requested quantity exceeds currently available stock."""


@dataclass(frozen=True)
class CustomBouquetFlower:
    flower_id: int
    flower_name: str
    quantity: int
    unit_price: Decimal


@dataclass(frozen=True)
class CustomBouquetPreview:
    bouquet: Bouquet
    flowers: list[CustomBouquetFlower]
    packaging_id: int | None
    packaging_name: str | None
    packaging_price: Decimal
    greeting_card_text: str | None
    greeting_card_price: Decimal
    occasion_ids: list[int]


class CustomBouquetService:
    """Build a custom bouquet from trusted catalog data using the GoF Builder."""

    def __init__(self, db: Session):
        self.flower_repository = FlowerRepository(db)
        self.packaging_repository = PackagingRepository(db)
        self.occasion_repository = OccasionRepository(db)

    def preview(
        self,
        *,
        name: str,
        flowers: list[tuple[int, int]],
        packaging_id: int | None = None,
        greeting_card_text: str | None = None,
        occasion_ids: list[int] | None = None,
    ) -> CustomBouquetPreview:
        if not flowers:
            raise CustomBouquetValidationError(
                "A custom bouquet must contain at least one flower"
            )

        flower_ids = [flower_id for flower_id, _ in flowers]
        if len(flower_ids) != len(set(flower_ids)):
            raise CustomBouquetValidationError(
                "The same flower cannot appear twice in a custom bouquet"
            )

        builder = CustomBouquetBuilder()
        flower_details: list[CustomBouquetFlower] = []

        for flower_id, quantity in flowers:
            flower = self.flower_repository.get_by_id(flower_id)
            if flower is None:
                raise CustomBouquetResourceNotFoundError(
                    f"Flower not found: {flower_id}"
                )
            if quantity <= 0:
                raise CustomBouquetValidationError(
                    "Flower quantity must be greater than zero"
                )
            if quantity > flower.stock_qty:
                raise InsufficientFlowerStockError(
                    f"Not enough {flower.name} in stock: requested {quantity}, "
                    f"available {flower.stock_qty}"
                )

            builder.add_flower(flower, quantity)
            flower_details.append(
                CustomBouquetFlower(
                    flower_id=flower.id,
                    flower_name=flower.name,
                    quantity=quantity,
                    unit_price=flower.unit_price,
                )
            )

        packaging_name: str | None = None
        packaging_price = Decimal("0.00")
        if packaging_id is not None:
            packaging = self.packaging_repository.get_by_id(packaging_id)
            if packaging is None or not packaging.is_active:
                raise CustomBouquetResourceNotFoundError(
                    f"Packaging option not found: {packaging_id}"
                )
            packaging_name = packaging.name
            packaging_price = packaging.price
            builder.set_packaging(packaging.name, packaging.price)

        normalized_card_text = (
            greeting_card_text.strip() if greeting_card_text is not None else None
        )
        if greeting_card_text is not None and not normalized_card_text:
            raise CustomBouquetValidationError(
                "Greeting card text cannot be empty"
            )
        greeting_card_price = Decimal("0.00")
        if normalized_card_text:
            greeting_card_price = GREETING_CARD_PRICE
            builder.add_greeting_card(normalized_card_text, GREETING_CARD_PRICE)

        normalized_occasion_ids = list(dict.fromkeys(occasion_ids or []))
        for occasion_id in normalized_occasion_ids:
            occasion = self.occasion_repository.get_by_id(occasion_id)
            if occasion is None or not occasion.is_active:
                raise CustomBouquetResourceNotFoundError(
                    f"Occasion not found: {occasion_id}"
                )

        bouquet = builder.build(name.strip())
        return CustomBouquetPreview(
            bouquet=bouquet,
            flowers=flower_details,
            packaging_id=packaging_id,
            packaging_name=packaging_name,
            packaging_price=packaging_price,
            greeting_card_text=normalized_card_text,
            greeting_card_price=greeting_card_price,
            occasion_ids=normalized_occasion_ids,
        )

    def build_order_item(
        self,
        *,
        name: str,
        flowers: list[tuple[int, int]],
        order_quantity: int,
        packaging_id: int | None = None,
        greeting_card_text: str | None = None,
        occasion_ids: list[int] | None = None,
    ) -> OrderItem:
        """Build a persistent order-item snapshot without publishing it to catalog."""
        if order_quantity <= 0:
            raise CustomBouquetValidationError(
                "Order item quantity must be greater than zero"
            )

        preview = self.preview(
            name=name,
            flowers=flowers,
            packaging_id=packaging_id,
            greeting_card_text=greeting_card_text,
            occasion_ids=occasion_ids,
        )

        # Preview validates one bouquet. Ordering several identical custom bouquets
        # must also fit the currently available stock.
        for flower in preview.flowers:
            requested_total = flower.quantity * order_quantity
            current = self.flower_repository.get_by_id(flower.flower_id)
            if current is None:
                raise CustomBouquetResourceNotFoundError(
                    f"Flower not found: {flower.flower_id}"
                )
            if requested_total > current.stock_qty:
                raise InsufficientFlowerStockError(
                    f"Not enough {current.name} in stock: requested {requested_total}, "
                    f"available {current.stock_qty}"
                )

        customization = {
            "flowers": [
                {
                    "flower_id": flower.flower_id,
                    "flower_name": flower.flower_name,
                    "quantity": flower.quantity,
                    "unit_price": str(flower.unit_price),
                }
                for flower in preview.flowers
            ],
            "packaging": (
                {
                    "id": preview.packaging_id,
                    "name": preview.packaging_name,
                    "price": str(preview.packaging_price),
                }
                if preview.packaging_id is not None
                else None
            ),
            "greeting_card": (
                {
                    "text": preview.greeting_card_text,
                    "price": str(preview.greeting_card_price),
                }
                if preview.greeting_card_text is not None
                else None
            ),
            "occasion_ids": preview.occasion_ids,
        }

        return OrderItem(
            bouquet_id=None,
            quantity=order_quantity,
            unit_price=preview.bouquet.base_price,
            item_name=preview.bouquet.name,
            item_description=preview.bouquet.description,
            is_custom=True,
            customization=customization,
        )
