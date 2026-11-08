import pytest

from app.patterns.observer import (
    ClientNotificationObserver,
    NotificationEvent,
    NotificationPublisher,
    NotificationType,
)


def test_subscribed_observer_receives_notification():
    publisher = NotificationPublisher()
    client = ClientNotificationObserver(client_id=1)
    publisher.subscribe(client)

    publisher.order_ready(order_id=42)

    assert len(client.events) == 1
    assert client.events[0].type == NotificationType.ORDER_READY
    assert "#42" in client.events[0].message


def test_multiple_observers_receive_same_event():
    publisher = NotificationPublisher()
    first = ClientNotificationObserver(client_id=1)
    second = ClientNotificationObserver(client_id=2)
    publisher.subscribe(first)
    publisher.subscribe(second)

    publisher.new_arrival("Autumn Roses")

    assert first.events == second.events
    assert first.events[0].type == NotificationType.NEW_ARRIVAL


def test_unsubscribed_observer_stops_receiving_events():
    publisher = NotificationPublisher()
    client = ClientNotificationObserver(client_id=1)
    publisher.subscribe(client)
    publisher.unsubscribe(client)

    publisher.bonus_accrued(100)

    assert client.events == ()


def test_duplicate_subscription_is_ignored():
    publisher = NotificationPublisher()
    client = ClientNotificationObserver(client_id=1)
    publisher.subscribe(client)
    publisher.subscribe(client)

    publisher.order_ready(7)

    assert len(publisher.observers) == 1
    assert len(client.events) == 1


def test_bonus_event_contains_amount():
    publisher = NotificationPublisher()
    client = ClientNotificationObserver(client_id=3)
    publisher.subscribe(client)

    publisher.bonus_accrued(250)

    event = client.events[0]
    assert event.type == NotificationType.BONUS_ACCRUED
    assert "250" in event.message


def test_empty_notification_message_is_rejected():
    with pytest.raises(ValueError):
        NotificationEvent(NotificationType.NEW_ARRIVAL, "   ")


def test_invalid_business_event_data_is_rejected():
    publisher = NotificationPublisher()

    with pytest.raises(ValueError):
        publisher.order_ready(0)
    with pytest.raises(ValueError):
        publisher.bonus_accrued(0)
    with pytest.raises(ValueError):
        publisher.new_arrival(" ")
