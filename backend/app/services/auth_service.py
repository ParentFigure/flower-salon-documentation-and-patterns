from __future__ import annotations

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository


class EmailAlreadyRegisteredError(ValueError):
    pass


class InvalidCredentialsError(ValueError):
    pass


class InactiveUserError(ValueError):
    pass


class AuthService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def register_client(
        self,
        *,
        email: str,
        password: str,
        full_name: str,
        phone: str | None = None,
    ) -> User:
        normalized_email = email.strip().lower()
        if self.user_repository.get_by_email(normalized_email) is not None:
            raise EmailAlreadyRegisteredError("Email is already registered")

        if not full_name.strip():
            raise ValueError("Full name is required")

        return self.user_repository.create_client(
            email=normalized_email,
            password_hash=hash_password(password),
            full_name=full_name,
            phone=phone,
        )

    def authenticate(self, email: str, password: str) -> User:
        user = self.user_repository.get_by_email(email)
        if user is None or not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid email or password")
        if not user.is_active:
            raise InactiveUserError("User account is inactive")
        return user

    def create_token(self, user: User) -> str:
        return create_access_token(user.id, user.role.value)
