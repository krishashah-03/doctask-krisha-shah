import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Document, Pile, Run
from app.db.session import get_db
from app.graph.build_graph import get_graph
from app.graph.nodes.examine_rules import RuleExaminationFailedError
from app.graph.nodes.extract import ExtractionFailedError, LLMProviderError
from app.graph.nodes.generate_deliverable import DeliverableDraftFailedError
from app.schemas import RunOut

router = APIRouter(tags=["pipeline"])

_VALIDATION_FAILURE_ERRORS = (ExtractionFailedError, DeliverableDraftFailedError, RuleExaminationFailedError)


def _thread_config(run_id: uuid.UUID | str) -> dict:
    return {"configurable": {"thread_id": str(run_id)}}


def _fail_run(db: Session, run: Run, exc: Exception) -> None:
    run.status = "failed"
    run.completed_at = datetime.now(timezone.utc)
    db.commit()
    if isinstance(exc, LLMProviderError):
        status_code = 502
    elif isinstance(exc, _VALIDATION_FAILURE_ERRORS):
        status_code = 422
    else:
        status_code = 500
    raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.post("/piles/{pile_id}/run", response_model=RunOut, status_code=201)
def run_pipeline(pile_id: uuid.UUID, db: Session = Depends(get_db)) -> Run:
    pile = db.get(Pile, pile_id)
    if pile is None:
        raise HTTPException(status_code=404, detail="Pile not found")

    document_ids = [
        str(document.id)
        for document in db.query(Document)
        .filter(Document.pile_id == pile_id, Document.status != "extracted")
        .all()
    ]

    run = Run(pile_id=pile_id, current_stage="extract")
    db.add(run)
    db.commit()
    db.refresh(run)

    if not document_ids:
        run.status = "completed"
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(run)
        return run

    graph = get_graph()
    initial_state = {
        "pile_id": str(pile_id),
        "run_id": str(run.id),
        "document_ids": document_ids,
        "current_stage": "extract",
        "created_fact_ids": [],
        "created_conflict_ids": [],
        "draft_sections": [],
        "draft_diff": [],
        "created_finding_ids": [],
    }

    try:
        graph.invoke(initial_state, _thread_config(run.id))
    except Exception as exc:
        _fail_run(db, run, exc)

    run.status = "completed"
    run.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)
    return run


@router.get("/runs/{run_id}", response_model=RunOut)
def get_run(run_id: uuid.UUID, db: Session = Depends(get_db)) -> Run:
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/runs/{run_id}/resume", response_model=RunOut)
def resume_run(run_id: uuid.UUID, db: Session = Depends(get_db)) -> Run:
    run = db.get(Run, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    graph = get_graph()
    config = _thread_config(run_id)

    snapshot = graph.get_state(config)
    if not snapshot.config:
        raise HTTPException(
            status_code=404,
            detail="No checkpoint found for this run — it was never started via /piles/{pile_id}/run",
        )
    if not snapshot.next:
        # Nothing left to resume; the graph already ran to completion.
        return run

    try:
        graph.invoke(None, config)
    except Exception as exc:
        _fail_run(db, run, exc)

    run.status = "completed"
    run.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)
    return run
