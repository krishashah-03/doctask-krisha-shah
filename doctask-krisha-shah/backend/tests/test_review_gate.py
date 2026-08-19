import uuid

from fastapi import HTTPException

from app.api.review import get_pending_review, submit_review_decision
from app.db.models import Conflict, Document, Fact, Finding, Rule, User
from app.schemas import ReviewDecisionCreate


def _make_user(db_session, role="reviewer"):
    user = User(email=f"test-{uuid.uuid4().hex}@example.com", display_name="Test User", role=role)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _make_document(db_session, pile):
    document = Document(
        pile_id=pile.id,
        doc_type="contract",
        storage_path=f"piles/{pile.id}/dummy-{uuid.uuid4().hex}.txt",
        content_hash=f"test-{uuid.uuid4().hex}",
        original_filename="doc.txt",
        mime_type="text/plain",
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document


def _make_fact(db_session, pile, fact_key="payment_term_days", fact_value="45"):
    document = _make_document(db_session, pile)
    fact = Fact(
        pile_id=pile.id,
        document_id=document.id,
        fact_key=fact_key,
        fact_value=fact_value,
        confidence=0.9,
        operation_id=f"test:{uuid.uuid4().hex}",
    )
    db_session.add(fact)
    db_session.commit()
    db_session.refresh(fact)
    return fact


def _make_conflict(db_session, pile, fact_a, fact_b):
    conflict = Conflict(
        pile_id=pile.id,
        fact_key=fact_a.fact_key,
        fact_id_a=fact_a.id,
        fact_id_b=fact_b.id,
        description="test conflict",
    )
    db_session.add(conflict)
    db_session.commit()
    db_session.refresh(conflict)
    return conflict


def _make_finding(db_session, pile):
    rule = Rule(pile_id=pile.id, rule_key="test_rule", description="test rule")
    db_session.add(rule)
    db_session.commit()
    db_session.refresh(rule)

    finding = Finding(pile_id=pile.id, rule_id=rule.id, description="test finding", severity="high")
    db_session.add(finding)
    db_session.commit()
    db_session.refresh(finding)
    return finding


def test_approving_one_conflict_does_not_affect_other_pending_items(db_session, test_pile):
    user = _make_user(db_session)
    fact_a = _make_fact(db_session, test_pile, fact_value="45")
    fact_b = _make_fact(db_session, test_pile, fact_value="60")
    fact_c = _make_fact(db_session, test_pile, fact_value="90")

    conflict_1 = _make_conflict(db_session, test_pile, fact_a, fact_b)
    conflict_2 = _make_conflict(db_session, test_pile, fact_a, fact_c)
    finding = _make_finding(db_session, test_pile)

    submit_review_decision(
        ReviewDecisionCreate(item_type="conflict", item_id=conflict_1.id, decision="approved", decided_by=user.id),
        db=db_session,
    )

    db_session.refresh(conflict_1)
    db_session.refresh(conflict_2)
    db_session.refresh(finding)

    assert conflict_1.status == "approved"
    assert conflict_2.status == "pending"
    assert finding.status == "pending"

    pending = get_pending_review(test_pile.id, db=db_session)
    pending_ids = {item.item_id for item in pending}
    assert conflict_1.id not in pending_ids
    assert conflict_2.id in pending_ids
    assert finding.id in pending_ids


def test_same_item_cannot_be_decided_twice(db_session, test_pile):
    user = _make_user(db_session)
    fact_a = _make_fact(db_session, test_pile, fact_value="45")
    fact_b = _make_fact(db_session, test_pile, fact_value="60")
    conflict = _make_conflict(db_session, test_pile, fact_a, fact_b)

    submit_review_decision(
        ReviewDecisionCreate(item_type="conflict", item_id=conflict.id, decision="approved", decided_by=user.id),
        db=db_session,
    )

    try:
        submit_review_decision(
            ReviewDecisionCreate(item_type="conflict", item_id=conflict.id, decision="rejected", decided_by=user.id),
            db=db_session,
        )
        assert False, "expected the second decision attempt to be rejected"
    except HTTPException as exc:
        assert exc.status_code == 409

    db_session.refresh(conflict)
    assert conflict.status == "approved"  # unchanged by the rejected second attempt


def test_decided_by_must_reference_a_real_user(db_session, test_pile):
    fact_a = _make_fact(db_session, test_pile, fact_value="45")
    fact_b = _make_fact(db_session, test_pile, fact_value="60")
    conflict = _make_conflict(db_session, test_pile, fact_a, fact_b)

    try:
        submit_review_decision(
            ReviewDecisionCreate(
                item_type="conflict", item_id=conflict.id, decision="approved", decided_by=uuid.uuid4()
            ),
            db=db_session,
        )
        assert False, "expected rejection for a nonexistent decided_by"
    except HTTPException as exc:
        assert exc.status_code == 422

    db_session.refresh(conflict)
    assert conflict.status == "pending"  # nothing was written
