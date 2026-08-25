import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import DeliverableVersion, Pile, Run, RunEvent
from app.db.session import get_db
from app.graph.nodes.generate_deliverable import (
    DeliverableCommitConflictError,
    DeliverableDraftFailedError,
    NoDraftFoundError,
    commit_deliverable,
    generate_deliverable,
)
from app.schemas import DeliverableCommitRequest, DeliverableVersionOut

router = APIRouter(prefix="/piles", tags=["deliverable"])


@router.post("/{pile_id}/generate-deliverable", status_code=201)
def generate_deliverable_draft(pile_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    """Standalone trigger for manual testing, same pattern as /extract and
    /detect-conflicts — the full graph (Phase 4) will call this node
    directly instead of going through HTTP.
    """
    pile = db.get(Pile, pile_id)
    if pile is None:
        raise HTTPException(status_code=404, detail="Pile not found")

    run = Run(pile_id=pile_id, current_stage="generate_deliverable")
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        outcome = generate_deliverable(pile_id=pile_id, run_id=run.id, db=db)
    except DeliverableDraftFailedError as exc:
        run.status = "failed"
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    run.status = "completed"
    run.completed_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "run_id": run.id,
        "sections": outcome.sections,
        "diff": outcome.diff,
        "included_fact_ids": outcome.included_fact_ids,
        "excluded_fact_ids": outcome.excluded_fact_ids,
    }


@router.get("/{pile_id}/deliverable/draft")
def get_pending_draft(pile_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    """The most recent generate-deliverable draft that hasn't been committed yet.

    Drafts only ever lived in run_events (see generate_deliverable's
    docstring) so a page refresh had nowhere to re-fetch one from — this
    makes that draft durable and reloadable instead of living only in the
    browser tab that triggered it.
    """
    pile = db.get(Pile, pile_id)
    if pile is None:
        raise HTTPException(status_code=404, detail="Pile not found")

    draft_event = (
        db.query(RunEvent)
        .join(Run, Run.id == RunEvent.run_id)
        .filter(Run.pile_id == pile_id, RunEvent.stage_name == "draft_deliverable")
        .order_by(RunEvent.created_at.desc())
        .first()
    )
    if draft_event is None:
        raise HTTPException(status_code=404, detail="No draft has been generated for this pile yet")

    already_committed = (
        db.query(DeliverableVersion)
        .filter(DeliverableVersion.based_on_run_id == draft_event.run_id)
        .first()
    )
    if already_committed is not None:
        raise HTTPException(status_code=404, detail="The latest draft was already committed")

    payload = draft_event.payload
    return {
        "run_id": draft_event.run_id,
        "sections": payload["sections"],
        "diff": payload["diff"],
        "included_fact_ids": payload["included_fact_ids"],
        "excluded_fact_ids": payload["excluded_fact_ids"],
        "generated_at": draft_event.created_at,
    }


@router.get("/{pile_id}/deliverable", response_model=DeliverableVersionOut)
def get_latest_deliverable(pile_id: uuid.UUID, db: Session = Depends(get_db)) -> DeliverableVersion:
    version = (
        db.query(DeliverableVersion)
        .filter(DeliverableVersion.pile_id == pile_id)
        .order_by(DeliverableVersion.version.desc())
        .first()
    )
    if version is None:
        raise HTTPException(status_code=404, detail="No deliverable has been committed for this pile yet")
    return version


@router.get("/{pile_id}/deliverable/history", response_model=list[DeliverableVersionOut])
def get_deliverable_history(pile_id: uuid.UUID, db: Session = Depends(get_db)) -> list[DeliverableVersion]:
    return (
        db.query(DeliverableVersion)
        .filter(DeliverableVersion.pile_id == pile_id)
        .order_by(DeliverableVersion.version.desc())
        .all()
    )


@router.post("/{pile_id}/deliverable/commit", response_model=DeliverableVersionOut, status_code=201)
def commit_deliverable_endpoint(
    pile_id: uuid.UUID, payload: DeliverableCommitRequest, db: Session = Depends(get_db)
) -> DeliverableVersion:
    pile = db.get(Pile, pile_id)
    if pile is None:
        raise HTTPException(status_code=404, detail="Pile not found")

    try:
        return commit_deliverable(pile_id=pile_id, run_id=payload.run_id, db=db)
    except NoDraftFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DeliverableCommitConflictError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
