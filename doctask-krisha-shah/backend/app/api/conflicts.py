import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Conflict, Pile, Run
from app.db.session import get_db
from app.graph.nodes.detect_conflicts import detect_conflicts
from app.schemas import ConflictDetectionResponse, ConflictOut

router = APIRouter(prefix="/piles", tags=["conflicts"])


@router.post("/{pile_id}/detect-conflicts", response_model=ConflictDetectionResponse)
def run_conflict_detection(pile_id: uuid.UUID, db: Session = Depends(get_db)) -> ConflictDetectionResponse:
    pile = db.get(Pile, pile_id)
    if pile is None:
        raise HTTPException(status_code=404, detail="Pile not found")

    run = Run(pile_id=pile_id, current_stage="detect_conflicts")
    db.add(run)
    db.commit()
    db.refresh(run)

    outcome = detect_conflicts(pile_id=pile_id, run_id=run.id, db=db)

    run.status = "completed"
    run.completed_at = datetime.now(timezone.utc)
    db.commit()

    return ConflictDetectionResponse(
        run_id=run.id,
        conflicts=[ConflictOut.model_validate(c) for c in outcome.conflicts],
    )


@router.get("/{pile_id}/conflicts", response_model=list[ConflictOut])
def list_conflicts(pile_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Conflict]:
    pile = db.get(Pile, pile_id)
    if pile is None:
        raise HTTPException(status_code=404, detail="Pile not found")

    return (
        db.query(Conflict)
        .filter(Conflict.pile_id == pile_id)
        .order_by(Conflict.detected_at.desc())
        .all()
    )
