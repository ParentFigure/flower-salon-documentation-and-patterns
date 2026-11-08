from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.client import Client


class ClientRepository:
    """Persistence operations for client profiles."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, client_id: int) -> Client | None:
        statement = (
            select(Client)
            .options(joinedload(Client.user))
            .where(Client.id == client_id)
        )
        return self.db.scalar(statement)

    def get_by_user_id(self, user_id: int) -> Client | None:
        statement = (
            select(Client)
            .options(joinedload(Client.user))
            .where(Client.user_id == user_id)
        )
        return self.db.scalar(statement)


    def list_all(self) -> list[Client]:
        statement = select(Client).order_by(Client.id.asc())
        return list(self.db.scalars(statement).all())

    def save(self, client: Client) -> Client:
        self.db.add(client)
        self.db.commit()
        self.db.refresh(client)
        return client
