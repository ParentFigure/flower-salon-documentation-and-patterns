from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.bouquet import Bouquet
from app.models.bouquet_item import BouquetItem
from app.models.flower import Flower
from app.models.occasion import Occasion


class BouquetRepository:
    """Data-access layer for Bouquet entities."""

    def __init__(self, db: Session):
        self.db = db

    def _with_catalog_relations(self):
        return (
            select(Bouquet)
            .options(
                selectinload(Bouquet.occasions),
                selectinload(Bouquet.items).selectinload(BouquetItem.flower),
            )
            .order_by(Bouquet.id)
        )

    def list_all(self, occasion_slug: str | None = None) -> list[Bouquet]:
        statement = self._with_catalog_relations()

        if occasion_slug:
            statement = (
                statement.join(Bouquet.occasions)
                .where(
                    Occasion.slug == occasion_slug,
                    Occasion.is_active.is_(True),
                )
            )

        return list(self.db.scalars(statement).unique().all())

    def get_by_id(self, bouquet_id: int) -> Bouquet | None:
        statement = self._with_catalog_relations().where(Bouquet.id == bouquet_id)
        return self.db.scalars(statement).unique().first()

    def create(self, bouquet: Bouquet) -> Bouquet:
        self.db.add(bouquet)
        self.db.commit()
        return self.get_by_id(bouquet.id) or bouquet

    def update(self, bouquet: Bouquet, **changes) -> Bouquet:
        for field, value in changes.items():
            setattr(bouquet, field, value)
        self.db.commit()
        return self.get_by_id(bouquet.id) or bouquet

    def set_occasions(self, bouquet: Bouquet, occasion_ids: list[int]) -> Bouquet:
        unique_ids = list(dict.fromkeys(occasion_ids))
        if not unique_ids:
            bouquet.occasions = []
        else:
            statement = select(Occasion).where(Occasion.id.in_(unique_ids))
            occasions = list(self.db.scalars(statement).all())
            found_ids = {occasion.id for occasion in occasions}
            missing_ids = [occasion_id for occasion_id in unique_ids if occasion_id not in found_ids]
            if missing_ids:
                raise LookupError(f"Occasion not found: {missing_ids[0]}")
            bouquet.occasions = occasions

        self.db.commit()
        return self.get_by_id(bouquet.id) or bouquet

    def set_composition(
        self,
        bouquet: Bouquet,
        composition: list[tuple[int, int]],
    ) -> Bouquet:
        flower_ids = [flower_id for flower_id, _ in composition]
        if len(flower_ids) != len(set(flower_ids)):
            raise ValueError("The same flower cannot appear twice in bouquet composition")

        for _, quantity in composition:
            if quantity <= 0:
                raise ValueError("Flower quantity must be greater than zero")

        unique_ids = list(dict.fromkeys(flower_ids))
        flowers_by_id: dict[int, Flower] = {}
        if unique_ids:
            statement = select(Flower).where(Flower.id.in_(unique_ids))
            flowers = list(self.db.scalars(statement).all())
            flowers_by_id = {flower.id: flower for flower in flowers}
            missing_ids = [flower_id for flower_id in unique_ids if flower_id not in flowers_by_id]
            if missing_ids:
                raise LookupError(f"Flower not found: {missing_ids[0]}")

        bouquet.items = [
            BouquetItem(
                flower=flowers_by_id[flower_id],
                quantity=quantity,
            )
            for flower_id, quantity in composition
        ]
        self.db.commit()
        return self.get_by_id(bouquet.id) or bouquet

    def delete(self, bouquet: Bouquet) -> None:
        self.db.delete(bouquet)
        self.db.commit()
