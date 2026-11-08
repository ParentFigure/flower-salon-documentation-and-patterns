from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Client, LoyaltyCardType, User, UserRole
from app.patterns.strategy.delivery import CourierDelivery, ExpressDelivery, PickupDelivery
from app.patterns.strategy.discount import GoldDiscount, NoDiscount, SocialDiscount
from app.repositories.loyalty_card_repository import LoyaltyCardRepository
from app.services.loyalty_service import (
    ClientNotFoundError,
    LoyaltyCardAlreadyExistsError,
    LoyaltyCardNotFoundError,
    LoyaltyService,
)


def build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def create_client(session: Session, email: str = "loyalty-service@example.com") -> Client:
    user = User(
        email=email,
        password_hash="hashed-password",
        role=UserRole.CLIENT,
    )
    client = Client(user=user, full_name="Loyalty Service Client")
    session.add(client)
    session.commit()
    return client


def build_service(session: Session) -> LoyaltyService:
    return LoyaltyService(LoyaltyCardRepository(session))


def test_issue_card_persists_requested_type():
    session = build_session()
    client = create_client(session)
    service = build_service(session)

    card = service.issue_card(client.id, LoyaltyCardType.GOLD)

    assert card.id is not None
    assert card.client_id == client.id
    assert card.card_type == LoyaltyCardType.GOLD
    assert service.get_card(client.id).id == card.id


def test_issue_card_rejects_missing_client_and_duplicate_card():
    session = build_session()
    client = create_client(session)
    service = build_service(session)

    with pytest.raises(ClientNotFoundError):
        service.issue_card(9999)

    service.issue_card(client.id)
    with pytest.raises(LoyaltyCardAlreadyExistsError):
        service.issue_card(client.id, LoyaltyCardType.SOCIAL)


def test_get_card_raises_when_client_has_no_card():
    session = build_session()
    client = create_client(session)
    service = build_service(session)

    with pytest.raises(LoyaltyCardNotFoundError):
        service.get_card(client.id)


def test_accrue_and_spend_bonus_are_persisted():
    session = build_session()
    client = create_client(session)
    service = build_service(session)
    service.issue_card(client.id, LoyaltyCardType.BONUS)

    accrued = service.accrue_bonus(client.id, Decimal("125.00"))
    assert accrued.bonus_balance == Decimal("125.00")

    spent = service.spend_bonus(client.id, Decimal("25.00"))
    assert spent.bonus_balance == Decimal("100.00")
    assert service.get_card(client.id).bonus_balance == Decimal("100.00")


def test_discount_strategy_is_selected_from_card_type():
    session = build_session()
    service = build_service(session)

    gold_client = create_client(session, "gold@example.com")
    social_client = create_client(session, "social@example.com")
    bonus_client = create_client(session, "bonus@example.com")

    service.issue_card(gold_client.id, LoyaltyCardType.GOLD)
    service.issue_card(social_client.id, LoyaltyCardType.SOCIAL)
    service.issue_card(bonus_client.id, LoyaltyCardType.BONUS)

    assert isinstance(service.discount_strategy_for(gold_client.id), GoldDiscount)
    assert isinstance(service.discount_strategy_for(social_client.id), SocialDiscount)
    assert isinstance(service.discount_strategy_for(bonus_client.id), NoDiscount)


def test_inactive_card_does_not_apply_percentage_discount():
    session = build_session()
    client = create_client(session)
    service = build_service(session)
    card = service.issue_card(client.id, LoyaltyCardType.GOLD)
    card.is_active = False
    service.repository.save(card)

    strategy = service.discount_strategy_for(client.id)

    assert isinstance(strategy, NoDiscount)


def test_gold_card_gets_free_courier_but_not_free_express():
    session = build_session()
    client = create_client(session)
    service = build_service(session)
    service.issue_card(client.id, LoyaltyCardType.GOLD)

    courier = service.delivery_strategy_for(client.id, "courier")
    express = service.delivery_strategy_for(client.id, "express")
    pickup = service.delivery_strategy_for(client.id, "pickup")

    assert isinstance(courier, CourierDelivery)
    assert courier.calculate_cost(Decimal("1000.00")) == Decimal("0.00")
    assert isinstance(express, ExpressDelivery)
    assert express.calculate_cost(Decimal("1000.00")) == Decimal("200.00")
    assert isinstance(pickup, PickupDelivery)


def test_regular_card_uses_standard_courier_fee_and_validates_delivery_type():
    session = build_session()
    client = create_client(session)
    service = build_service(session)
    service.issue_card(client.id, LoyaltyCardType.BONUS)

    courier = service.delivery_strategy_for(client.id, "courier")

    assert courier.calculate_cost(Decimal("1000.00")) == Decimal("100.00")
    with pytest.raises(ValueError, match="Unsupported delivery type"):
        service.delivery_strategy_for(client.id, "drone")
