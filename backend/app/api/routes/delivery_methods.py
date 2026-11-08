from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.db.session import get_db
from app.models.delivery_method import DeliveryMethod
from app.models.user import User
from app.repositories.delivery_method_repository import DeliveryMethodRepository
from app.schemas.delivery_method import (
    DeliveryMethodCreate,
    DeliveryMethodRead,
    DeliveryMethodUpdate,
)

router = APIRouter(prefix="/delivery-methods", tags=["delivery-methods"])


def _get_method_or_404(
    repository: DeliveryMethodRepository,
    method_id: int,
) -> DeliveryMethod:
    method = repository.get_by_id(method_id)
    if method is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery method not found",
        )
    return method


def _ensure_unique(
    repository: DeliveryMethodRepository,
    *,
    code: str,
    name: str,
    current_id: int | None = None,
) -> None:
    by_code = repository.get_by_code(code)
    if by_code is not None and by_code.id != current_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Delivery method with this code already exists",
        )

    by_name = repository.get_by_name(name)
    if by_name is not None and by_name.id != current_id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Delivery method with this name already exists",
        )


@router.get("", response_model=list[DeliveryMethodRead])
def list_delivery_methods(db: Session = Depends(get_db)):
    return DeliveryMethodRepository(db).list_all(active_only=True)


@router.get("/admin/all", response_model=list[DeliveryMethodRead])
def list_all_for_admin(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    return DeliveryMethodRepository(db).list_all(active_only=False)


@router.get("/{method_id}", response_model=DeliveryMethodRead)
def get_delivery_method(method_id: int, db: Session = Depends(get_db)):
    return _get_method_or_404(DeliveryMethodRepository(db), method_id)


@router.post(
    "",
    response_model=DeliveryMethodRead,
    status_code=status.HTTP_201_CREATED,
)
def create_delivery_method(
    payload: DeliveryMethodCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    repository = DeliveryMethodRepository(db)
    _ensure_unique(repository, code=payload.code, name=payload.name)
    return repository.create(DeliveryMethod(**payload.model_dump()))


@router.put("/{method_id}", response_model=DeliveryMethodRead)
def update_delivery_method(
    method_id: int,
    payload: DeliveryMethodUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    repository = DeliveryMethodRepository(db)
    method = _get_method_or_404(repository, method_id)
    _ensure_unique(
        repository,
        code=payload.code,
        name=payload.name,
        current_id=method.id,
    )
    return repository.update(method, **payload.model_dump())


@router.delete("/{method_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_delivery_method(
    method_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    repository = DeliveryMethodRepository(db)
    method = _get_method_or_404(repository, method_id)
    repository.delete(method)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
