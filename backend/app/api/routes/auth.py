from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import CurrentUserRead, LoginRequest, RegisterRequest, TokenResponse
from app.services.auth_service import (
    AuthService,
    EmailAlreadyRegisteredError,
    InactiveUserError,
    InvalidCredentialsError,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _service(db: Session) -> AuthService:
    return AuthService(UserRepository(db))


def _user_response(user: User) -> CurrentUserRead:
    return CurrentUserRead(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        client_id=user.client.id if user.client is not None else None,
    )


@router.post("/register", response_model=CurrentUserRead, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    try:
        user = _service(db).register_client(
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
            phone=payload.phone,
        )
        return _user_response(user)
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    try:
        service = _service(db)
        user = service.authenticate(payload.email, payload.password)
        return TokenResponse(access_token=service.create_token(user))
    except (InvalidCredentialsError, InactiveUserError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.get("/me", response_model=CurrentUserRead)
def me(current_user: User = Depends(get_current_user)):
    return _user_response(current_user)
