from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.db.session import get_db
from app.models.salon import Salon
from app.models.user import User
from app.repositories.salon_repository import SalonRepository
from app.schemas.salon import SalonCreate, SalonRead, SalonUpdate

router = APIRouter(prefix="/salons", tags=["salons"])


def _get_salon_or_404(repository: SalonRepository, salon_id: int) -> Salon:
    salon = repository.get_by_id(salon_id)
    if salon is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Salon not found",
        )
    return salon


def _ensure_unique_name(
    repository: SalonRepository,
    name: str,
    current_id: int | None = None,
) -> None:
    existing = repository.get_by_name(name)
    if existing is not None and existing.id != current_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Salon with this name already exists",
        )


@router.get("", response_model=list[SalonRead])
def list_salons(db: Session = Depends(get_db)):
    return SalonRepository(db).list_all(active_only=True)


@router.get("/admin/all", response_model=list[SalonRead])
def list_all_for_admin(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return SalonRepository(db).list_all(active_only=False)


@router.get("/{salon_id}", response_model=SalonRead)
def get_salon(salon_id: int, db: Session = Depends(get_db)):
    return _get_salon_or_404(SalonRepository(db), salon_id)


@router.post("", response_model=SalonRead, status_code=status.HTTP_201_CREATED)
def create_salon(
    payload: SalonCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    repository = SalonRepository(db)
    _ensure_unique_name(repository, payload.name)
    return repository.create(Salon(**payload.model_dump()))


@router.put("/{salon_id}", response_model=SalonRead)
def update_salon(
    salon_id: int,
    payload: SalonUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    repository = SalonRepository(db)
    salon = _get_salon_or_404(repository, salon_id)
    _ensure_unique_name(repository, payload.name, current_id=salon.id)
    return repository.update(salon, **payload.model_dump())


@router.delete("/{salon_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_salon(
    salon_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    repository = SalonRepository(db)
    salon = _get_salon_or_404(repository, salon_id)
    repository.delete(salon)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
