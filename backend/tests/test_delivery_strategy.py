from decimal import Decimal

import pytest

from app.patterns.strategy import (
    CourierDelivery,
    DeliveryCostCalculator,
    ExpressDelivery,
    PickupDelivery,
)


def test_pickup_delivery_is_free():
    strategy = PickupDelivery()

    assert strategy.name == "pickup"
    assert strategy.calculate_cost(Decimal("850.00")) == Decimal("0.00")


def test_courier_delivery_uses_standard_fee():
    strategy = CourierDelivery()

    assert strategy.name == "courier"
    assert strategy.calculate_cost(Decimal("1250.00")) == Decimal("100.00")


def test_express_delivery_uses_higher_fee():
    strategy = ExpressDelivery()

    assert strategy.name == "express"
    assert strategy.calculate_cost(Decimal("1250.00")) == Decimal("200.00")


def test_context_can_switch_delivery_strategy_at_runtime():
    calculator = DeliveryCostCalculator(PickupDelivery())
    subtotal = Decimal("1000.00")

    assert calculator.calculate(subtotal) == Decimal("0.00")

    calculator.set_strategy(CourierDelivery(fee=Decimal("120.00")))

    assert calculator.calculate(subtotal) == Decimal("120.00")


def test_delivery_strategy_rejects_negative_subtotal():
    calculator = DeliveryCostCalculator(CourierDelivery())

    with pytest.raises(ValueError, match="cannot be negative"):
        calculator.calculate(Decimal("-1.00"))
