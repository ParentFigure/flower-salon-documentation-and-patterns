from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.db.session import get_db
from app.models.flower import Flower
from app.models.user import User
from app.repositories.flower_repository import FlowerRepository
from app.schemas.flower import FlowerCreate, FlowerRead, FlowerUpdate

router = APIRouter(prefix="/flowers", tags=["flowers"])


def _get_flower_or_404(repository: FlowerRepository, flower_id: int) -> Flower:
    flower = repository.get_by_id(flower_id)
    if flower is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Flower not found",
        )
    return flower


@router.get("", response_model=list[FlowerRead])
def list_flowers(db: Session = Depends(get_db)):
    return FlowerRepository(db).list_all()


@router.get("/{flower_id}", response_model=FlowerRead)
def get_flower(flower_id: int, db: Session = Depends(get_db)):
    repository = FlowerRepository(db)
    return _get_flower_or_404(repository, flower_id)


@router.post("", response_model=FlowerRead, status_code=status.HTTP_201_CREATED)
def create_flower(
    payload: FlowerCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    repository = FlowerRepository(db)
    if repository.get_by_name(payload.name) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Flower with this name already exists",
        )
    return repository.create(Flower(**payload.model_dump()))


@router.put("/{flower_id}", response_model=FlowerRead)
def update_flower(
    flower_id: int,
    payload: FlowerUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    repository = FlowerRepository(db)
    flower = _get_flower_or_404(repository, flower_id)

    duplicate = repository.get_by_name(payload.name)
    if duplicate is not None and duplicate.id != flower.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Flower with this name already exists",
        )

    return repository.update(flower, **payload.model_dump())


@router.delete("/{flower_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_flower(
    flower_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    repository = FlowerRepository(db)
    flower = _get_flower_or_404(repository, flower_id)
    repository.delete(flower)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
