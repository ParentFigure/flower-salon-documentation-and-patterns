from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.db.session import get_db
from app.models.occasion import Occasion
from app.models.user import User
from app.repositories.occasion_repository import OccasionRepository
from app.schemas.occasion import OccasionCreate, OccasionRead, OccasionUpdate

router = APIRouter(prefix="/occasions", tags=["occasions"])


def _get_occasion_or_404(
    repository: OccasionRepository,
    occasion_id: int,
) -> Occasion:
    occasion = repository.get_by_id(occasion_id)
    if occasion is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Occasion not found",
        )
    return occasion


def _ensure_unique(
    repository: OccasionRepository,
    *,
    name: str,
    slug: str,
    current_id: int | None = None,
) -> None:
    by_name = repository.get_by_name(name)
    if by_name is not None and by_name.id != current_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Occasion with this name already exists",
        )

    by_slug = repository.get_by_slug(slug)
    if by_slug is not None and by_slug.id != current_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Occasion with this slug already exists",
        )


@router.get("", response_model=list[OccasionRead])
def list_occasions(db: Session = Depends(get_db)):
    return OccasionRepository(db).list_all(active_only=True)


@router.get("/{occasion_id}", response_model=OccasionRead)
def get_occasion(occasion_id: int, db: Session = Depends(get_db)):
    return _get_occasion_or_404(OccasionRepository(db), occasion_id)


@router.post("", response_model=OccasionRead, status_code=status.HTTP_201_CREATED)
def create_occasion(
    payload: OccasionCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    repository = OccasionRepository(db)
    _ensure_unique(repository, name=payload.name, slug=payload.slug)
    return repository.create(Occasion(**payload.model_dump()))


@router.put("/{occasion_id}", response_model=OccasionRead)
def update_occasion(
    occasion_id: int,
    payload: OccasionUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    repository = OccasionRepository(db)
    occasion = _get_occasion_or_404(repository, occasion_id)
    _ensure_unique(
        repository,
        name=payload.name,
        slug=payload.slug,
        current_id=occasion.id,
    )
    return repository.update(occasion, **payload.model_dump())


@router.delete("/{occasion_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_occasion(
    occasion_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    repository = OccasionRepository(db)
    occasion = _get_occasion_or_404(repository, occasion_id)
    repository.delete(occasion)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
