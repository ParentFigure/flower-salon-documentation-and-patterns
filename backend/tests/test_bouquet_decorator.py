from decimal import Decimal

import pytest

from app.models.bouquet import Bouquet
from app.patterns.decorator import (
    BasicBouquet,
    GreetingCardDecorator,
    PackagingDecorator,
    RibbonDecorator,
)


def make_bouquet() -> Bouquet:
    return Bouquet(
        name="Birthday roses",
        description="Classic bouquet",
        base_price=Decimal("500.00"),
        is_custom=False,
    )


def test_basic_bouquet_exposes_original_name_and_price():
    component = BasicBouquet(make_bouquet())

    assert component.get_description() == "Birthday roses"
    assert component.get_price() == Decimal("500.00")


def test_packaging_decorator_adds_description_and_price():
    decorated = PackagingDecorator(
        BasicBouquet(make_bouquet()),
        packaging_name="Kraft paper",
        price=Decimal("70.00"),
    )

    assert decorated.get_description() == "Birthday roses, packaging: Kraft paper"
    assert decorated.get_price() == Decimal("570.00")


def test_decorators_can_be_combined_in_any_sequence():
    decorated = GreetingCardDecorator(
        RibbonDecorator(
            PackagingDecorator(
                BasicBouquet(make_bouquet()),
                packaging_name="Gift box",
                price=Decimal("100.00"),
            ),
            ribbon_color="red",
            price=Decimal("20.00"),
        ),
        text="Happy birthday!",
        price=Decimal("25.00"),
    )

    assert decorated.get_price() == Decimal("645.00")
    assert decorated.get_description() == (
        'Birthday roses, packaging: Gift box, red ribbon, card: "Happy birthday!"'
    )


def test_decorators_do_not_modify_original_bouquet():
    bouquet = make_bouquet()
    decorated = RibbonDecorator(BasicBouquet(bouquet), "white", Decimal("30.00"))

    assert decorated.get_price() == Decimal("530.00")
    assert bouquet.base_price == Decimal("500.00")
    assert bouquet.name == "Birthday roses"


def test_decorator_rejects_negative_price():
    with pytest.raises(ValueError, match="cannot be negative"):
        PackagingDecorator(
            BasicBouquet(make_bouquet()),
            "Kraft paper",
            Decimal("-1.00"),
        )


def test_decorators_validate_required_text_values():
    component = BasicBouquet(make_bouquet())

    with pytest.raises(ValueError, match="Packaging name"):
        PackagingDecorator(component, "   ")

    with pytest.raises(ValueError, match="Ribbon color"):
        RibbonDecorator(component, "   ")

    with pytest.raises(ValueError, match="Greeting card text"):
        GreetingCardDecorator(component, "   ")
