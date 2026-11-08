from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Client, LoyaltyCard, LoyaltyCardType, User, UserRole


def build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def create_client(session: Session) -> Client:
    user = User(
        email="loyalty@example.com",
        password_hash="hashed-password",
        role=UserRole.CLIENT,
    )
    client = Client(user=user, full_name="Loyalty Client", phone="+380000000001")
    session.add(client)
    session.commit()
    return client


def test_bonus_card_has_zero_balance_by_default():
    session = build_session()
    client = create_client(session)

    card = LoyaltyCard(client_id=client.id, card_type=LoyaltyCardType.BONUS)
    session.add(card)
    session.commit()
    session.refresh(card)

    assert card.bonus_balance == Decimal("0.00")
    assert card.discount_percent == Decimal("0.00")
    assert card.free_delivery is False


def test_gold_card_has_discount_and_free_delivery():
    card = LoyaltyCard(card_type=LoyaltyCardType.GOLD)

    assert card.discount_percent == Decimal("10.00")
    assert card.free_delivery is True


def test_social_card_has_social_discount_without_free_delivery():
    card = LoyaltyCard(card_type=LoyaltyCardType.SOCIAL)

    assert card.discount_percent == Decimal("15.00")
    assert card.free_delivery is False


def test_bonus_balance_can_be_accrued_and_spent():
    card = LoyaltyCard(
        card_type=LoyaltyCardType.BONUS,
        bonus_balance=Decimal("100.00"),
    )

    assert card.add_bonus(Decimal("50.00")) == Decimal("150.00")
    assert card.spend_bonus(Decimal("40.00")) == Decimal("110.00")


def test_bonus_operations_validate_amounts_and_balance():
    card = LoyaltyCard(
        card_type=LoyaltyCardType.BONUS,
        bonus_balance=Decimal("20.00"),
    )

    with pytest.raises(ValueError, match="positive"):
        card.add_bonus(Decimal("0.00"))

    with pytest.raises(ValueError, match="Not enough bonuses"):
        card.spend_bonus(Decimal("30.00"))
