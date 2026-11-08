from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.db.session import get_db
from app.models.bouquet import Bouquet
from app.models.user import User
from app.repositories.bouquet_repository import BouquetRepository
from app.schemas.bouquet import BouquetCreate, BouquetRead

router = APIRouter(prefix="/bouquets", tags=["bouquets"])


@router.get("", response_model=list[BouquetRead])
def list_bouquets(db: Session = Depends(get_db)):
    repository = BouquetRepository(db)
    return repository.list_all()


@router.get("/{bouquet_id}", response_model=BouquetRead)
def get_bouquet(bouquet_id: int, db: Session = Depends(get_db)):
    repository = BouquetRepository(db)
    bouquet = repository.get_by_id(bouquet_id)

    if bouquet is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bouquet not found",
        )

    return bouquet


@router.post("", response_model=BouquetRead, status_code=status.HTTP_201_CREATED)
def create_bouquet(
    payload: BouquetCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    repository = BouquetRepository(db)
    bouquet = Bouquet(**payload.model_dump())
    return repository.create(bouquet)
