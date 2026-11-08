from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.bouquet import Bouquet
from app.schemas.bouquet import BouquetRead

router = APIRouter(prefix="/bouquets", tags=["bouquets"])

@router.get("", response_model=list[BouquetRead])
def list_bouquets(db: Session = Depends(get_db)):
    return db.scalars(select(Bouquet)).all()
