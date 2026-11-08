from decimal import Decimal

import pytest

from app.patterns.strategy import (
    BonusDiscount,
    DiscountCalculator,
    EventDiscount,
    GoldDiscount,
    NoDiscount,
    SocialDiscount,
)


def test_no_discount_keeps_original_price():
    calculator = DiscountCalculator(NoDiscount())

    assert calculator.calculate(Decimal("1000.00")) == Decimal("1000.00")


def test_gold_discount_applies_default_percentage():
    strategy = GoldDiscount()

    assert strategy.name == "gold"
    assert strategy.apply(Decimal("1000.00")) == Decimal("900.00")


def test_social_discount_applies_default_percentage():
    strategy = SocialDiscount()

    assert strategy.name == "social"
    assert strategy.apply(Decimal("1000.00")) == Decimal("850.00")


def test_event_discount_can_use_custom_percentage():
    strategy = EventDiscount("Valentine's Day", percent=Decimal("20.00"))

    assert strategy.event_name == "Valentine's Day"
    assert strategy.apply(Decimal("750.00")) == Decimal("600.00")


def test_bonus_discount_never_makes_total_negative():
    strategy = BonusDiscount(Decimal("800.00"))

    assert strategy.apply(Decimal("500.00")) == Decimal("0.00")


def test_context_can_switch_discount_strategy_at_runtime():
    calculator = DiscountCalculator(NoDiscount())
    subtotal = Decimal("1200.00")

    assert calculator.calculate(subtotal) == Decimal("1200.00")

    calculator.set_strategy(GoldDiscount(percent=Decimal("5.00")))

    assert calculator.calculate(subtotal) == Decimal("1140.00")


def test_discount_strategies_validate_invalid_values():
    with pytest.raises(ValueError, match="between 0 and 100"):
        GoldDiscount(percent=Decimal("101.00"))

    with pytest.raises(ValueError, match="cannot be negative"):
        DiscountCalculator(NoDiscount()).calculate(Decimal("-1.00"))

    with pytest.raises(ValueError, match="Event name"):
        EventDiscount("   ")
