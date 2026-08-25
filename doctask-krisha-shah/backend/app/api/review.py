import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Conflict, Finding, Pile, ReviewDecision, User
from app.db.session import get_db
from app.schemas import PendingReviewItem, ReviewDecisionCreate, ReviewDecisionOut

router = APIRouter(tags=["review"])

_ITEM_MODELS = {"conflict": Conflict, "finding": Finding}


@router.get("/piles/{pile_id}/pending-review", response_model=list[PendingReviewItem])
def get_pending_review(pile_id: uuid.UUID, db: Session = Depends(get_db)) -> list[PendingReviewItem]:
    pile = db.get(Pile, pile_id)
    if pile is None:
        raise HTTPException(status_code=404, detail="Pile not found")

    items: list[PendingReviewItem] = []

    conflicts = db.query(Conflict).filter(Conflict.pile_id == pile_id, Conflict.status == "pending").all()
    for conflict in conflicts:
        items.append(
            PendingReviewItem(
                item_type="conflict",
                item_id=conflict.id,
                pile_id=conflict.pile_id,
                description=conflict.description,
                status=conflict.status,
                detail={
                    "fact_key": conflict.fact_key,
                    "fact_id_a": str(conflict.fact_id_a),
                    "fact_id_b": str(conflict.fact_id_b),
                    "run_id": str(conflict.run_id) if conflict.run_id else None,
                    "detected_at": conflict.detected_at.isoformat(),
                },
            )
        )

    findings = db.query(Finding).filter(Finding.pile_id == pile_id, Finding.status == "pending").all()
    for finding in findings:
        items.append(
            PendingReviewItem(
                item_type="finding",
                item_id=finding.id,
                pile_id=finding.pile_id,
                description=finding.description,
                status=finding.status,
                detail={
                    "rule_id": str(finding.rule_id) if finding.rule_id else None,
                    "document_id": str(finding.document_id) if finding.document_id else None,
                    "severity": finding.severity,
                    "char_start": finding.char_start,
                    "char_end": finding.char_end,
                    "run_id": str(finding.run_id) if finding.run_id else None,
                },
            )
        )

    return items


@router.post("/review-decisions", response_model=ReviewDecisionOut, status_code=201)
def submit_review_decision(
    payload: ReviewDecisionCreate, db: Session = Depends(get_db)
) -> ReviewDecision:
    if payload.item_type not in _ITEM_MODELS:
        raise HTTPException(
            status_code=422,
            detail=f"item_type must be one of {sorted(_ITEM_MODELS)} (deliverable_update review is not yet supported)",
        )
    if payload.decision not in ("approved", "rejected"):
        raise HTTPException(status_code=422, detail="decision must be 'approved' or 'rejected'")

    user = db.get(User, payload.decided_by)
    if user is None:
        raise HTTPException(status_code=422, detail=f"decided_by {payload.decided_by} does not reference a real user")

    model = _ITEM_MODELS[payload.item_type]
    item = db.get(model, payload.item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"{payload.item_type} {payload.item_id} not found")

    if item.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"{payload.item_type} {payload.item_id} was already decided (status={item.status})",
        )

    decision = ReviewDecision(
        item_type=payload.item_type,
        item_id=payload.item_id,
        run_id=payload.run_id,
        decision=payload.decision,
        decided_by=payload.decided_by,
    )
    db.add(decision)

    item.status = payload.decision
    db.commit()
    db.refresh(decision)
    return decision


@router.get("/review-decisions", response_model=list[ReviewDecisionOut])
def list_review_decisions(pile_id: uuid.UUID, db: Session = Depends(get_db)) -> list[ReviewDecision]:
    pile = db.get(Pile, pile_id)
    if pile is None:
        raise HTTPException(status_code=404, detail="Pile not found")

    conflict_ids = {row.id for row in db.query(Conflict.id).filter(Conflict.pile_id == pile_id).all()}
    finding_ids = {row.id for row in db.query(Finding.id).filter(Finding.pile_id == pile_id).all()}
    all_ids = conflict_ids | finding_ids
    if not all_ids:
        return []

    return (
        db.query(ReviewDecision)
        .filter(ReviewDecision.item_id.in_(all_ids))
        .order_by(ReviewDecision.decided_at.desc())
        .all()
    )
