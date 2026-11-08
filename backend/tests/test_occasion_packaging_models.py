from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.models import Bouquet, Occasion, Packaging
from app.repositories import OccasionRepository, PackagingRepository


def make_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_occasion_can_represent_required_event_categories():
    with make_session() as db:
        repo = OccasionRepository(db)
        for name, slug in [
            ("Wedding", "wedding"),
            ("Birthday", "birthday"),
            ("Valentine's Day", "valentine"),
            ("Funeral", "funeral"),
        ]:
            repo.create(Occasion(name=name, slug=slug))

        assert [item.slug for item in repo.list_all()] == [
            "birthday",
            "funeral",
            "valentine",
            "wedding",
        ]


def test_occasion_repository_can_find_by_slug():
    with make_session() as db:
        repo = OccasionRepository(db)
        occasion = repo.create(Occasion(name="Birthday", slug="birthday"))

        found = repo.get_by_slug("birthday")
        assert found is not None
        assert found.id == occasion.id


def test_active_only_filters_disabled_occasions():
    with make_session() as db:
        repo = OccasionRepository(db)
        repo.create(Occasion(name="Wedding", slug="wedding", is_active=True))
        repo.create(Occasion(name="Old Event", slug="old-event", is_active=False))

        assert [item.slug for item in repo.list_all(active_only=True)] == ["wedding"]


def test_bouquet_can_have_multiple_occasions():
    with make_session() as db:
        birthday = Occasion(name="Birthday", slug="birthday")
        valentine = Occasion(name="Valentine's Day", slug="valentine")
        bouquet = Bouquet(
            name="Red Roses",
            description="Universal romantic bouquet",
            base_price=Decimal("950.00"),
            occasions=[birthday, valentine],
        )
        db.add(bouquet)
        db.commit()
        db.refresh(bouquet)

        assert {occasion.slug for occasion in bouquet.occasions} == {
            "birthday",
            "valentine",
        }


def test_packaging_repository_creates_and_finds_option():
    with make_session() as db:
        repo = PackagingRepository(db)
        packaging = repo.create(
            Packaging(
                name="Craft paper",
                description="Minimal eco-style wrapping",
                price=Decimal("70.00"),
            )
        )

        found = repo.get_by_name("Craft paper")
        assert found is not None
        assert found.id == packaging.id
        assert found.price == Decimal("70.00")


def test_packaging_active_only_filter():
    with make_session() as db:
        repo = PackagingRepository(db)
        repo.create(Packaging(name="Gift box", price=Decimal("150.00")))
        repo.create(
            Packaging(
                name="Archived wrap",
                price=Decimal("20.00"),
                is_active=False,
            )
        )

        assert [item.name for item in repo.list_all(active_only=True)] == ["Gift box"]


def test_packaging_price_cannot_be_negative():
    with make_session() as db:
        db.add(Packaging(name="Invalid", price=Decimal("-1.00")))
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        else:
            raise AssertionError("Negative packaging price must violate DB constraint")


def test_occasion_and_packaging_names_are_unique():
    with make_session() as db:
        db.add_all(
            [
                Occasion(name="Wedding", slug="wedding"),
                Occasion(name="Wedding", slug="second-wedding"),
            ]
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        else:
            raise AssertionError("Occasion name must be unique")

        db.add_all(
            [
                Packaging(name="Craft paper", price=Decimal("10.00")),
                Packaging(name="Craft paper", price=Decimal("20.00")),
            ]
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
        else:
            raise AssertionError("Packaging name must be unique")
