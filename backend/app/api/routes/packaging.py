from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.db.session import get_db
from app.models.packaging import Packaging
from app.models.user import User
from app.repositories.packaging_repository import PackagingRepository
from app.schemas.packaging import PackagingCreate, PackagingRead, PackagingUpdate

router = APIRouter(prefix="/packaging", tags=["packaging"])


def _get_packaging_or_404(
    repository: PackagingRepository,
    packaging_id: int,
) -> Packaging:
    packaging = repository.get_by_id(packaging_id)
    if packaging is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Packaging option not found",
        )
    return packaging


@router.get("", response_model=list[PackagingRead])
def list_packaging(db: Session = Depends(get_db)):
    return PackagingRepository(db).list_all(active_only=True)


@router.get("/{packaging_id}", response_model=PackagingRead)
def get_packaging(packaging_id: int, db: Session = Depends(get_db)):
    return _get_packaging_or_404(PackagingRepository(db), packaging_id)


@router.post("", response_model=PackagingRead, status_code=status.HTTP_201_CREATED)
def create_packaging(
    payload: PackagingCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    repository = PackagingRepository(db)
    if repository.get_by_name(payload.name) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Packaging option with this name already exists",
        )
    return repository.create(Packaging(**payload.model_dump()))


@router.put("/{packaging_id}", response_model=PackagingRead)
def update_packaging(
    packaging_id: int,
    payload: PackagingUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    repository = PackagingRepository(db)
    packaging = _get_packaging_or_404(repository, packaging_id)

    duplicate = repository.get_by_name(payload.name)
    if duplicate is not None and duplicate.id != packaging.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Packaging option with this name already exists",
        )

    return repository.update(packaging, **payload.model_dump())


@router.delete("/{packaging_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_packaging(
    packaging_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    repository = PackagingRepository(db)
    packaging = _get_packaging_or_404(repository, packaging_id)
    repository.delete(packaging)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
