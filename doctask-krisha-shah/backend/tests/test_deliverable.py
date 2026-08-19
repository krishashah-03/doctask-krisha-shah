import threading
import uuid

from app.db.models import Conflict, DeliverableVersion, Document, Fact, Run
from app.db.session import SessionLocal
from app.graph.nodes.generate_deliverable import (
    DeliverableCommitConflictError,
    NoDraftFoundError,
    commit_deliverable,
    generate_deliverable,
)


def _make_document(session, pile, name="doc.txt"):
    document = Document(
        pile_id=pile.id,
        doc_type="contract",
        storage_path=f"piles/{pile.id}/dummy-{uuid.uuid4().hex}.txt",
        content_hash=f"test-{uuid.uuid4().hex}",
        original_filename=name,
        mime_type="text/plain",
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


def _make_fact(session, pile, document, fact_key, fact_value, *, superseded_by=None):
    fact = Fact(
        pile_id=pile.id,
        document_id=document.id,
        fact_key=fact_key,
        fact_value=fact_value,
        confidence=0.9,
        operation_id=f"test:{uuid.uuid4().hex}",
        superseded_by=superseded_by,
    )
    session.add(fact)
    session.commit()
    session.refresh(fact)
    return fact


def _make_conflict(session, pile, fact_key, fact_a, fact_b, status="pending"):
    conflict = Conflict(
        pile_id=pile.id,
        fact_key=fact_key,
        fact_id_a=fact_a.id,
        fact_id_b=fact_b.id,
        description="test conflict",
        status=status,
    )
    session.add(conflict)
    session.commit()
    session.refresh(conflict)
    return conflict


def _make_run(session, pile):
    run = Run(pile_id=pile.id, current_stage="generate_deliverable")
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def test_generate_deliverable_excludes_facts_tied_to_pending_conflicts(db_session, test_pile):
    doc_a = _make_document(db_session, test_pile, "a.txt")
    doc_b = _make_document(db_session, test_pile, "b.txt")
    doc_c = _make_document(db_session, test_pile, "c.txt")

    conflicted_a = _make_fact(db_session, test_pile, doc_a, "payment_term_days", "45")
    conflicted_b = _make_fact(db_session, test_pile, doc_b, "payment_term_days", "60")
    _make_conflict(db_session, test_pile, "payment_term_days", conflicted_a, conflicted_b)

    safe_fact = _make_fact(db_session, test_pile, doc_c, "delivery_date", "30 April 2026")

    run = _make_run(db_session, test_pile)
    outcome = generate_deliverable(pile_id=test_pile.id, run_id=run.id, db=db_session)

    assert conflicted_a.id not in outcome.included_fact_ids
    assert conflicted_b.id not in outcome.included_fact_ids
    assert safe_fact.id in outcome.included_fact_ids

    all_cited_fact_ids = {
        citation["fact_id"] for section in outcome.sections for citation in section["citations"]
    }
    assert str(conflicted_a.id) not in all_cited_fact_ids
    assert str(conflicted_b.id) not in all_cited_fact_ids
    assert str(safe_fact.id) in all_cited_fact_ids


def test_superseded_fact_falls_back_when_superseder_is_excluded(db_session, test_pile):
    doc_contract = _make_document(db_session, test_pile, "contract.txt")
    doc_amendment = _make_document(db_session, test_pile, "amendment.txt")
    doc_other = _make_document(db_session, test_pile, "other.txt")

    amendment_fact = _make_fact(db_session, test_pile, doc_amendment, "payment_term_days", "60")
    contract_fact = _make_fact(
        db_session,
        test_pile,
        doc_contract,
        "payment_term_days",
        "45",
        superseded_by=amendment_fact.id,
    )
    other_fact = _make_fact(db_session, test_pile, doc_other, "payment_term_days", "90")
    # The amendment's fact is tied to a pending conflict -> excluded. Since
    # its superseder is excluded, the older contract fact must NOT vanish.
    _make_conflict(db_session, test_pile, "payment_term_days", amendment_fact, other_fact)

    run = _make_run(db_session, test_pile)
    outcome = generate_deliverable(pile_id=test_pile.id, run_id=run.id, db=db_session)

    assert amendment_fact.id not in outcome.included_fact_ids
    assert contract_fact.id in outcome.included_fact_ids


def test_commit_twice_with_same_run_id_does_not_double_insert(db_session, test_pile):
    doc = _make_document(db_session, test_pile)
    _make_fact(db_session, test_pile, doc, "delivery_date", "30 April 2026")

    run = _make_run(db_session, test_pile)
    generate_deliverable(pile_id=test_pile.id, run_id=run.id, db=db_session)

    first = commit_deliverable(pile_id=test_pile.id, run_id=run.id, db=db_session)
    second = commit_deliverable(pile_id=test_pile.id, run_id=run.id, db=db_session)

    assert first.id == second.id
    assert first.version == second.version

    total = (
        db_session.query(DeliverableVersion)
        .filter(DeliverableVersion.pile_id == test_pile.id)
        .count()
    )
    assert total == 1


def test_commit_without_draft_raises(db_session, test_pile):
    run = _make_run(db_session, test_pile)
    try:
        commit_deliverable(pile_id=test_pile.id, run_id=run.id, db=db_session)
        assert False, "expected NoDraftFoundError"
    except NoDraftFoundError:
        pass


def test_concurrent_commits_one_succeeds_one_gets_clean_conflict(real_pile):
    setup_session = SessionLocal()
    try:
        doc = _make_document(setup_session, real_pile)
        _make_fact(setup_session, real_pile, doc, "delivery_date", "30 April 2026")

        run_a = _make_run(setup_session, real_pile)
        run_b = _make_run(setup_session, real_pile)

        # Two independent drafts on the same pile, so both commits will
        # legitimately compute the same next_version and race for it.
        generate_deliverable(pile_id=real_pile.id, run_id=run_a.id, db=setup_session)
        generate_deliverable(pile_id=real_pile.id, run_id=run_b.id, db=setup_session)

        pile_id, run_a_id, run_b_id = real_pile.id, run_a.id, run_b.id
    finally:
        setup_session.close()

    barrier = threading.Barrier(2)
    results = {}

    def _commit(run_id, key):
        session = SessionLocal()
        try:
            version_row = commit_deliverable(
                pile_id=pile_id,
                run_id=run_id,
                db=session,
                _on_after_read_version=lambda: barrier.wait(timeout=5),
            )
            results[key] = ("ok", version_row.version)
        except DeliverableCommitConflictError as exc:
            results[key] = ("conflict", exc.version)
        finally:
            session.close()

    thread_a = threading.Thread(target=_commit, args=(run_a_id, "a"))
    thread_b = threading.Thread(target=_commit, args=(run_b_id, "b"))
    thread_a.start()
    thread_b.start()
    thread_a.join(timeout=15)
    thread_b.join(timeout=15)

    outcomes = [results["a"], results["b"]]
    successes = [o for o in outcomes if o[0] == "ok"]
    conflicts = [o for o in outcomes if o[0] == "conflict"]

    assert len(successes) == 1, f"expected exactly one success, got {outcomes}"
    assert len(conflicts) == 1, f"expected exactly one clean conflict, got {outcomes}"
    assert successes[0][1] == conflicts[0][1]  # both raced for the same version number

    verify_session = SessionLocal()
    try:
        rows = (
            verify_session.query(DeliverableVersion)
            .filter(DeliverableVersion.pile_id == pile_id)
            .all()
        )
        versions = [row.version for row in rows]
        assert versions == sorted(set(versions))  # no duplicate version numbers
        assert len(rows) == 1
    finally:
        verify_session.close()
