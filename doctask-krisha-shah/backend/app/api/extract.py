import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Document, Fact, Pile, Run
from app.db.session import get_db
from app.graph.nodes.extract import ExtractionFailedError, LLMProviderError, extract_document
from app.schemas import ExtractionResponse, FactOut, InjectionFlagOut

router = APIRouter(prefix="/piles", tags=["extraction"])


@router.get("/{pile_id}/facts", response_model=list[FactOut])
def list_facts(pile_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Fact]:
    pile = db.get(Pile, pile_id)
    if pile is None:
        raise HTTPException(status_code=404, detail="Pile not found")

    return db.query(Fact).filter(Fact.pile_id == pile_id).order_by(Fact.created_at.desc()).all()


@router.post(
    "/{pile_id}/documents/{document_id}/extract",
    response_model=ExtractionResponse,
)
def run_extraction(
    pile_id: uuid.UUID, document_id: uuid.UUID, db: Session = Depends(get_db)
) -> ExtractionResponse:
    document = db.get(Document, document_id)
    if document is None or document.pile_id != pile_id:
        raise HTTPException(status_code=404, detail="Document not found in this pile")

    run = Run(pile_id=pile_id, current_stage="extract")
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        outcome = extract_document(document_id=document.id, run_id=run.id, db=db)
    except ExtractionFailedError as exc:
        run.status = "failed"
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LLMProviderError as exc:
        run.status = "failed"
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    run.status = "completed"
    run.completed_at = datetime.now(timezone.utc)
    db.commit()

    return ExtractionResponse(
        run_id=run.id,
        facts=[FactOut.model_validate(f) for f in outcome.facts],
        injection_flags=[InjectionFlagOut.model_validate(f) for f in outcome.injection_flags],
    )
