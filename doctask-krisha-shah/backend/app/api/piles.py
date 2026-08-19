import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Pile
from app.db.session import get_db
from app.schemas import PileCreate, PileOut

router = APIRouter(prefix="/piles", tags=["piles"])


@router.post("", response_model=PileOut, status_code=201)
def create_pile(payload: PileCreate, db: Session = Depends(get_db)) -> Pile:
    pile = Pile(name=payload.name, domain=payload.domain, owner_user_id=payload.owner_user_id)
    db.add(pile)
    db.commit()
    db.refresh(pile)
    return pile


@router.get("", response_model=list[PileOut])
def list_piles(db: Session = Depends(get_db)) -> list[Pile]:
    return db.query(Pile).order_by(Pile.created_at.desc()).all()


@router.get("/{pile_id}", response_model=PileOut)
def get_pile(pile_id: uuid.UUID, db: Session = Depends(get_db)) -> Pile:
    pile = db.get(Pile, pile_id)
    if pile is None:
        raise HTTPException(status_code=404, detail="Pile not found")
    return pile
