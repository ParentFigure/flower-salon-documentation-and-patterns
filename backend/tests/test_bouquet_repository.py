from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models.bouquet import Bouquet
from app.repositories.bouquet_repository import BouquetRepository


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_create_and_get_bouquet():
    with make_session() as db:
        repository = BouquetRepository(db)
        bouquet = Bouquet(
            name="Spring Mood",
            description="Tulips and seasonal greenery",
            base_price=Decimal("850.00"),
            is_custom=False,
        )

        created = repository.create(bouquet)
        loaded = repository.get_by_id(created.id)

        assert created.id is not None
        assert loaded is not None
        assert loaded.name == "Spring Mood"
        assert loaded.base_price == Decimal("850.00")


def test_list_all_bouquets_returns_saved_items():
    with make_session() as db:
        repository = BouquetRepository(db)
        repository.create(
            Bouquet(name="Rose Classic", base_price=Decimal("1200.00"), is_custom=False)
        )
        repository.create(
            Bouquet(name="Custom Mix", base_price=Decimal("950.00"), is_custom=True)
        )

        bouquets = repository.list_all()

        assert [bouquet.name for bouquet in bouquets] == ["Rose Classic", "Custom Mix"]


def test_get_by_id_returns_none_for_missing_bouquet():
    with make_session() as db:
        repository = BouquetRepository(db)

        assert repository.get_by_id(999) is None
