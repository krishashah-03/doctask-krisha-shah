import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Finding, Pile, Rule, Run
from app.db.session import get_db
from app.graph.nodes.examine_rules import RuleExaminationFailedError, examine_rules
from app.schemas import FindingOut, RuleCreate, RuleOut

router = APIRouter(prefix="/piles", tags=["rules"])


@router.post("/{pile_id}/rules", response_model=RuleOut, status_code=201)
def create_rule(pile_id: uuid.UUID, payload: RuleCreate, db: Session = Depends(get_db)) -> Rule:
    pile = db.get(Pile, pile_id)
    if pile is None:
        raise HTTPException(status_code=404, detail="Pile not found")

    rule = Rule(
        pile_id=pile_id,
        rule_key=payload.rule_key,
        description=payload.description,
        rule_spec=payload.rule_spec,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("/{pile_id}/rules", response_model=list[RuleOut])
def list_rules(pile_id: uuid.UUID, db: Session = Depends(get_db)) -> list[Rule]:
    return db.query(Rule).filter(Rule.pile_id == pile_id).order_by(Rule.created_at.desc()).all()


@router.get("/{pile_id}/findings", response_model=list[FindingOut])
def list_findings(
    pile_id: uuid.UUID, status: str | None = None, db: Session = Depends(get_db)
) -> list[Finding]:
    query = db.query(Finding).filter(Finding.pile_id == pile_id)
    if status is not None:
        query = query.filter(Finding.status == status)
    return query.order_by(Finding.created_at.desc()).all()


@router.post("/{pile_id}/examine-rules", status_code=201)
def run_rule_examination(pile_id: uuid.UUID, db: Session = Depends(get_db)) -> dict:
    """Standalone trigger for manual testing, same pattern as /extract,
    /detect-conflicts, and /generate-deliverable — the full graph (Phase 4)
    will call this node directly instead of going through HTTP.
    """
    pile = db.get(Pile, pile_id)
    if pile is None:
        raise HTTPException(status_code=404, detail="Pile not found")

    run = Run(pile_id=pile_id, current_stage="examine_rules")
    db.add(run)
    db.commit()
    db.refresh(run)

    try:
        outcome = examine_rules(pile_id=pile_id, run_id=run.id, db=db)
    except RuleExaminationFailedError as exc:
        run.status = "failed"
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    run.status = "completed"
    run.completed_at = datetime.now(timezone.utc)
    db.commit()

    return {
        "run_id": run.id,
        "findings": [FindingOut.model_validate(f) for f in outcome.findings],
    }
