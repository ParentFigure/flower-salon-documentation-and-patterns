from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.db.session import get_db
from app.models.bouquet import Bouquet
from app.models.user import User
from app.repositories.bouquet_repository import BouquetRepository
from app.schemas.bouquet import (
    BouquetCreate,
    BouquetFlowerRead,
    BouquetOccasionRead,
    BouquetRead,
    BouquetUpdate,
)

router = APIRouter(prefix="/bouquets", tags=["bouquets"])


def _get_bouquet_or_404(repository: BouquetRepository, bouquet_id: int) -> Bouquet:
    bouquet = repository.get_by_id(bouquet_id)
    if bouquet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bouquet not found",
        )
    return bouquet


def _serialize_bouquet(bouquet: Bouquet) -> BouquetRead:
    return BouquetRead(
        id=bouquet.id,
        name=bouquet.name,
        description=bouquet.description,
        base_price=bouquet.base_price,
        is_custom=bouquet.is_custom,
        occasions=[
            BouquetOccasionRead(id=occasion.id, name=occasion.name, slug=occasion.slug)
            for occasion in bouquet.occasions
        ],
        composition=[
            BouquetFlowerRead(
                flower_id=item.flower_id,
                flower_name=item.flower.name,
                quantity=item.quantity,
            )
            for item in bouquet.items
        ],
    )


def _apply_catalog_relations(
    repository: BouquetRepository,
    bouquet: Bouquet,
    occasion_ids: list[int],
    composition: list,
) -> Bouquet:
    try:
        bouquet = repository.set_occasions(bouquet, occasion_ids)
        bouquet = repository.set_composition(
            bouquet,
            [(item.flower_id, item.quantity) for item in composition],
        )
        return bouquet
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@router.get("", response_model=list[BouquetRead])
def list_bouquets(
    occasion: str | None = Query(default=None, min_length=1, max_length=100),
    db: Session = Depends(get_db),
):
    bouquets = BouquetRepository(db).list_all(occasion_slug=occasion)
    return [_serialize_bouquet(bouquet) for bouquet in bouquets]


@router.get("/{bouquet_id}", response_model=BouquetRead)
def get_bouquet(bouquet_id: int, db: Session = Depends(get_db)):
    bouquet = _get_bouquet_or_404(BouquetRepository(db), bouquet_id)
    return _serialize_bouquet(bouquet)


@router.post("", response_model=BouquetRead, status_code=status.HTTP_201_CREATED)
def create_bouquet(
    payload: BouquetCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    repository = BouquetRepository(db)
    data = payload.model_dump(exclude={"occasion_ids", "composition"})
    bouquet = repository.create(Bouquet(**data))
    bouquet = _apply_catalog_relations(
        repository,
        bouquet,
        payload.occasion_ids,
        payload.composition,
    )
    return _serialize_bouquet(bouquet)


@router.put("/{bouquet_id}", response_model=BouquetRead)
def update_bouquet(
    bouquet_id: int,
    payload: BouquetUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    repository = BouquetRepository(db)
    bouquet = _get_bouquet_or_404(repository, bouquet_id)
    data = payload.model_dump(exclude={"occasion_ids", "composition"})
    bouquet = repository.update(bouquet, **data)
    bouquet = _apply_catalog_relations(
        repository,
        bouquet,
        payload.occasion_ids,
        payload.composition,
    )
    return _serialize_bouquet(bouquet)


@router.delete("/{bouquet_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bouquet(
    bouquet_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    repository = BouquetRepository(db)
    bouquet = _get_bouquet_or_404(repository, bouquet_id)
    repository.delete(bouquet)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
