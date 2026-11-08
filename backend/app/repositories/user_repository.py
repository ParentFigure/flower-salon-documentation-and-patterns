from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.user import User, UserRole


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        statement = select(User).where(User.email == email.strip().lower())
        return self.db.scalar(statement)

    def create_client(
        self,
        *,
        email: str,
        password_hash: str,
        full_name: str,
        phone: str | None = None,
    ) -> User:
        user = User(
            email=email.strip().lower(),
            password_hash=password_hash,
            role=UserRole.CLIENT,
            is_active=True,
        )
        user.client = Client(
            full_name=full_name.strip(),
            phone=phone.strip() if phone else None,
        )

        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
