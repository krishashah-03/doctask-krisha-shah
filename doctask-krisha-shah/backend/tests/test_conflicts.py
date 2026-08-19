import uuid

from app.db.models import Conflict, Document, Fact, Run
from app.graph.nodes.detect_conflicts import detect_conflicts


def _make_document(db_session, pile, name):
    document = Document(
        pile_id=pile.id,
        doc_type="contract",
        storage_path=f"piles/{pile.id}/dummy-{uuid.uuid4().hex}.txt",
        content_hash=f"test-{uuid.uuid4().hex}",
        original_filename=name,
        mime_type="text/plain",
    )
    db_session.add(document)
    db_session.commit()
    db_session.refresh(document)
    return document


def _make_fact(db_session, pile, document, fact_key, fact_value, *, superseded_by=None):
    fact = Fact(
        pile_id=pile.id,
        document_id=document.id,
        fact_key=fact_key,
        fact_value=fact_value,
        confidence=0.9,
        operation_id=f"test:{uuid.uuid4().hex}",
        superseded_by=superseded_by,
    )
    db_session.add(fact)
    db_session.commit()
    db_session.refresh(fact)
    return fact


def _make_run(db_session, pile):
    run = Run(pile_id=pile.id, current_stage="detect_conflicts")
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run


def test_conflicting_facts_across_documents_are_flagged(db_session, test_pile):
    contract = _make_document(db_session, test_pile, "contract.txt")
    amendment = _make_document(db_session, test_pile, "amendment.txt")

    _make_fact(db_session, test_pile, contract, "payment_term_days", "45")
    _make_fact(db_session, test_pile, amendment, "payment_term_days", "60")

    run = _make_run(db_session, test_pile)
    outcome = detect_conflicts(pile_id=test_pile.id, run_id=run.id, db=db_session)

    assert len(outcome.conflicts) == 1
    conflict = outcome.conflicts[0]
    assert conflict.fact_key == "payment_term_days"
    assert conflict.status == "pending"
    assert {conflict.fact_id_a, conflict.fact_id_b} == {
        db_session.query(Fact).filter(Fact.document_id == contract.id).first().id,
        db_session.query(Fact).filter(Fact.document_id == amendment.id).first().id,
    }


def test_same_document_facts_never_conflict(db_session, test_pile):
    document = _make_document(db_session, test_pile, "doc.txt")
    _make_fact(db_session, test_pile, document, "payment_term_days", "45")
    _make_fact(db_session, test_pile, document, "payment_term_days", "60")

    run = _make_run(db_session, test_pile)
    outcome = detect_conflicts(pile_id=test_pile.id, run_id=run.id, db=db_session)

    assert outcome.conflicts == []


def test_matching_values_across_documents_do_not_conflict(db_session, test_pile):
    doc_a = _make_document(db_session, test_pile, "a.txt")
    doc_b = _make_document(db_session, test_pile, "b.txt")
    _make_fact(db_session, test_pile, doc_a, "payment_term_days", "45")
    _make_fact(db_session, test_pile, doc_b, "payment_term_days", "45")

    run = _make_run(db_session, test_pile)
    outcome = detect_conflicts(pile_id=test_pile.id, run_id=run.id, db=db_session)

    assert outcome.conflicts == []


def test_detection_is_idempotent(db_session, test_pile):
    doc_a = _make_document(db_session, test_pile, "a.txt")
    doc_b = _make_document(db_session, test_pile, "b.txt")
    _make_fact(db_session, test_pile, doc_a, "payment_term_days", "45")
    _make_fact(db_session, test_pile, doc_b, "payment_term_days", "60")

    run1 = _make_run(db_session, test_pile)
    outcome1 = detect_conflicts(pile_id=test_pile.id, run_id=run1.id, db=db_session)
    assert len(outcome1.conflicts) == 1

    run2 = _make_run(db_session, test_pile)
    outcome2 = detect_conflicts(pile_id=test_pile.id, run_id=run2.id, db=db_session)
    assert outcome2.conflicts == []  # already flagged, no duplicate row

    total = db_session.query(Conflict).filter(Conflict.pile_id == test_pile.id).count()
    assert total == 1


def test_superseded_facts_are_still_compared(db_session, test_pile):
    contract = _make_document(db_session, test_pile, "contract.txt")
    amendment = _make_document(db_session, test_pile, "amendment.txt")

    amendment_fact = _make_fact(db_session, test_pile, amendment, "payment_term_days", "60")
    contract_fact = _make_fact(
        db_session,
        test_pile,
        contract,
        "payment_term_days",
        "45",
        superseded_by=amendment_fact.id,
    )

    run = _make_run(db_session, test_pile)
    outcome = detect_conflicts(pile_id=test_pile.id, run_id=run.id, db=db_session)

    assert len(outcome.conflicts) == 1
    assert {outcome.conflicts[0].fact_id_a, outcome.conflicts[0].fact_id_b} == {
        contract_fact.id,
        amendment_fact.id,
    }
