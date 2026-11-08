from decimal import Decimal

import pytest

from app.models.flower import Flower
from app.patterns.builder import CustomBouquetBuilder


def make_flower(name: str, price: str) -> Flower:
    return Flower(name=name, unit_price=Decimal(price), stock_qty=100)


def test_builder_creates_custom_bouquet_with_calculated_price():
    rose = make_flower("Rose", "80.00")
    tulip = make_flower("Tulip", "45.00")

    bouquet = (
        CustomBouquetBuilder()
        .add_flower(rose, 5)
        .add_flower(tulip, 3)
        .set_packaging("Craft paper", "70.00")
        .add_greeting_card("Happy birthday!", "25.00")
        .build("Birthday bouquet")
    )

    assert bouquet.name == "Birthday bouquet"
    assert bouquet.base_price == Decimal("630.00")
    assert bouquet.is_custom is True
    assert "Rose x5" in bouquet.description
    assert "Tulip x3" in bouquet.description
    assert "Packaging: Craft paper" in bouquet.description
    assert 'Card: "Happy birthday!"' in bouquet.description


def test_builder_allows_optional_packaging_and_card():
    rose = make_flower("Rose", "80.00")

    bouquet = CustomBouquetBuilder().add_flower(rose, 2).build()

    assert bouquet.base_price == Decimal("160.00")
    assert bouquet.description == "Flowers: Rose x2"


def test_builder_rejects_non_positive_flower_quantity():
    rose = make_flower("Rose", "80.00")
    builder = CustomBouquetBuilder()

    with pytest.raises(ValueError, match="greater than zero"):
        builder.add_flower(rose, 0)


def test_builder_requires_at_least_one_flower():
    builder = CustomBouquetBuilder().set_packaging("Box", "100.00")

    with pytest.raises(ValueError, match="at least one flower"):
        builder.build()


def test_builder_resets_after_build():
    rose = make_flower("Rose", "80.00")
    builder = CustomBouquetBuilder().add_flower(rose, 1)

    builder.build()

    with pytest.raises(ValueError, match="at least one flower"):
        builder.build()
