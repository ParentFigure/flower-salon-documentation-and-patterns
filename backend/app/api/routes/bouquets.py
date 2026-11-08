from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.db.session import get_db
from app.models.bouquet import Bouquet
from app.models.user import User
from app.repositories.bouquet_repository import BouquetRepository
from app.schemas.bouquet import BouquetCreate, BouquetRead, BouquetUpdate

router = APIRouter(prefix="/bouquets", tags=["bouquets"])


def _get_bouquet_or_404(repository: BouquetRepository, bouquet_id: int) -> Bouquet:
    bouquet = repository.get_by_id(bouquet_id)
    if bouquet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bouquet not found",
        )
    return bouquet


@router.get("", response_model=list[BouquetRead])
def list_bouquets(db: Session = Depends(get_db)):
    return BouquetRepository(db).list_all()


@router.get("/{bouquet_id}", response_model=BouquetRead)
def get_bouquet(bouquet_id: int, db: Session = Depends(get_db)):
    return _get_bouquet_or_404(BouquetRepository(db), bouquet_id)


@router.post("", response_model=BouquetRead, status_code=status.HTTP_201_CREATED)
def create_bouquet(
    payload: BouquetCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    repository = BouquetRepository(db)
    return repository.create(Bouquet(**payload.model_dump()))


@router.put("/{bouquet_id}", response_model=BouquetRead)
def update_bouquet(
    bouquet_id: int,
    payload: BouquetUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    repository = BouquetRepository(db)
    bouquet = _get_bouquet_or_404(repository, bouquet_id)
    return repository.update(bouquet, **payload.model_dump())


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
