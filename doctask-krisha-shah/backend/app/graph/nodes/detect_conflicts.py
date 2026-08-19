import itertools
import uuid
from dataclasses import dataclass

from sqlalchemy import and_, or_, text
from sqlalchemy.orm import Session

from app.db.models import Conflict, Document, Fact


def _conflict_already_exists(db: Session, fact_id_a: uuid.UUID, fact_id_b: uuid.UUID) -> bool:
    existing = (
        db.query(Conflict.id)
        .filter(
            or_(
                and_(Conflict.fact_id_a == fact_id_a, Conflict.fact_id_b == fact_id_b),
                and_(Conflict.fact_id_a == fact_id_b, Conflict.fact_id_b == fact_id_a),
            )
        )
        .first()
    )
    return existing is not None


def _describe(db: Session, fact_a: Fact, fact_b: Fact) -> str:
    doc_a = db.get(Document, fact_a.document_id)
    doc_b = db.get(Document, fact_b.document_id)
    name_a = (doc_a.original_filename if doc_a else None) or str(fact_a.document_id)
    name_b = (doc_b.original_filename if doc_b else None) or str(fact_b.document_id)
    return (
        f"Fact '{fact_a.fact_key}' has conflicting values: "
        f"'{fact_a.fact_value}' (from {name_a}) vs '{fact_b.fact_value}' (from {name_b})"
    )


@dataclass
class ConflictDetectionOutcome:
    conflicts: list[Conflict]


def detect_conflicts(
    pile_id: uuid.UUID | str, run_id: uuid.UUID | str, db: Session
) -> ConflictDetectionOutcome:
    """Flags facts that disagree with each other within a pile.

    Two facts conflict when they share a fact_key, come from different
    documents, and have different values. Superseded facts are still
    compared — a fact being superseded is itself often the interesting
    conflict (e.g. an invoice that cites pre-amendment terms).

    The exists-check-then-insert below isn't atomic on its own — conflicts
    has no unique constraint on the fact pair, unlike facts' operation_id.
    A Postgres advisory lock scoped to this pile serializes concurrent
    calls for the SAME pile (transaction-scoped: released automatically at
    commit), so two runs racing on one pile can't both insert the same
    conflict; calls for different piles never block each other.
    """
    db.execute(text("SELECT pg_advisory_xact_lock(hashtext(:pile_id))"), {"pile_id": str(pile_id)})

    facts = db.query(Fact).filter(Fact.pile_id == pile_id).all()

    by_key: dict[str, list[Fact]] = {}
    for fact in facts:
        by_key.setdefault(fact.fact_key, []).append(fact)

    created: list[Conflict] = []
    for fact_key, group in by_key.items():
        for fact_a, fact_b in itertools.combinations(group, 2):
            if fact_a.document_id == fact_b.document_id:
                continue
            if fact_a.fact_value == fact_b.fact_value:
                continue
            if _conflict_already_exists(db, fact_a.id, fact_b.id):
                continue

            conflict = Conflict(
                pile_id=pile_id,
                fact_key=fact_key,
                fact_id_a=fact_a.id,
                fact_id_b=fact_b.id,
                description=_describe(db, fact_a, fact_b),
                run_id=run_id,
            )
            db.add(conflict)
            created.append(conflict)

    db.commit()
    return ConflictDetectionOutcome(conflicts=created)
