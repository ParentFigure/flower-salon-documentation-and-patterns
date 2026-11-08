import pytest

from app.patterns.state import InvalidOrderStateTransition, OrderStateContext


def test_order_starts_in_created_state():
    order = OrderStateContext()

    assert order.status == "created"
    assert order.history == ("created",)


def test_order_can_follow_full_happy_path():
    order = OrderStateContext()

    order.confirm()
    order.start_preparing()
    order.mark_ready()
    order.start_delivery()
    order.complete()

    assert order.status == "completed"
    assert order.history == (
        "created",
        "confirmed",
        "preparing",
        "ready",
        "delivering",
        "completed",
    )


def test_created_order_can_be_cancelled():
    order = OrderStateContext()

    order.cancel()

    assert order.status == "cancelled"


def test_confirmed_order_can_be_cancelled():
    order = OrderStateContext()
    order.confirm()

    order.cancel()

    assert order.status == "cancelled"


def test_cannot_start_preparing_before_confirmation():
    order = OrderStateContext()

    with pytest.raises(InvalidOrderStateTransition):
        order.start_preparing()

    assert order.status == "created"


def test_preparing_order_cannot_be_cancelled():
    order = OrderStateContext()
    order.confirm()
    order.start_preparing()

    with pytest.raises(InvalidOrderStateTransition):
        order.cancel()

    assert order.status == "preparing"


def test_completed_order_is_terminal():
    order = OrderStateContext()
    order.confirm()
    order.start_preparing()
    order.mark_ready()
    order.start_delivery()
    order.complete()

    with pytest.raises(InvalidOrderStateTransition):
        order.cancel()

    assert order.status == "completed"


def test_cancelled_order_is_terminal():
    order = OrderStateContext()
    order.cancel()

    with pytest.raises(InvalidOrderStateTransition):
        order.confirm()

    assert order.status == "cancelled"
