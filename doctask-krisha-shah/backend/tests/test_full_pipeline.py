import uuid

from app.db.models import Conflict, DeliverableVersion, Document, Fact, Finding, Rule, Run, RunEvent
from app.db.session import SessionLocal
from app.graph.build_graph import get_checkpointer, get_graph
from app.storage.local_fs import LocalFileStorage


def _make_document_with_content(session, pile, text, name):
    storage = LocalFileStorage(pile_id=str(pile.id))
    storage_path = storage.save(text.encode("utf-8"), ext="txt")

    document = Document(
        pile_id=pile.id,
        doc_type="contract",
        storage_path=storage_path,
        content_hash=f"test-{uuid.uuid4().hex}",
        original_filename=name,
        mime_type="text/plain",
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


def _clear_checkpoints(thread_id: str) -> None:
    checkpointer = get_checkpointer()
    with checkpointer.conn.connection() as conn:
        conn.execute("DELETE FROM checkpoint_writes WHERE thread_id = %s", (thread_id,))
        conn.execute("DELETE FROM checkpoint_blobs WHERE thread_id = %s", (thread_id,))
        conn.execute("DELETE FROM checkpoints WHERE thread_id = %s", (thread_id,))


def test_full_pipeline_produces_facts_conflict_draft_and_findings_without_committing(real_pile):
    setup_session = SessionLocal()
    try:
        # Small synthetic documents, crafted so the mock extractor's
        # "Label: value" regex reliably captures a genuinely conflicting
        # fact — the large sample files use unstructured prose for this
        # clause, which the mock (deliberately simple) can't parse.
        doc_a = _make_document_with_content(
            setup_session, real_pile, "Payment Terms: 45 days from invoice date.\n", "contract.txt"
        )
        doc_b = _make_document_with_content(
            setup_session, real_pile, "Payment Terms: 60 days from invoice date.\n", "amendment.txt"
        )

        # A rule guaranteed to flag both facts above (45 and 60 both > 30).
        rule = Rule(
            pile_id=real_pile.id,
            rule_key="payment_term_max_days",
            description="Payment terms must not exceed 30 days",
            rule_spec={"max_days": 30},
        )
        setup_session.add(rule)
        setup_session.commit()

        run = Run(pile_id=real_pile.id, current_stage="extract")
        setup_session.add(run)
        setup_session.commit()
        setup_session.refresh(run)

        pile_id, doc_a_id, doc_b_id, run_id = real_pile.id, doc_a.id, doc_b.id, run.id
    finally:
        setup_session.close()

    graph = get_graph()
    config = {"configurable": {"thread_id": str(run_id)}}
    initial_state = {
        "pile_id": str(pile_id),
        "run_id": str(run_id),
        "document_ids": [str(doc_a_id), str(doc_b_id)],
        "current_stage": "extract",
        "created_fact_ids": [],
        "created_conflict_ids": [],
        "draft_sections": [],
        "draft_diff": [],
        "created_finding_ids": [],
    }

    try:
        graph.invoke(initial_state, config)

        verify_session = SessionLocal()
        try:
            facts = verify_session.query(Fact).filter(Fact.pile_id == pile_id).all()
            assert len(facts) > 0

            conflicts = verify_session.query(Conflict).filter(Conflict.pile_id == pile_id).all()
            assert len(conflicts) == 1
            assert conflicts[0].status == "pending"

            draft_event = (
                verify_session.query(RunEvent)
                .filter(RunEvent.run_id == run_id, RunEvent.stage_name == "draft_deliverable")
                .first()
            )
            assert draft_event is not None
            assert "sections" in draft_event.payload

            findings = verify_session.query(Finding).filter(Finding.pile_id == pile_id).all()
            assert len(findings) > 0
            assert all(f.status == "pending" for f in findings)

            # The whole point of Phase 4: nothing auto-commits. A draft
            # sits in run_events; deliverable_versions stays untouched
            # until POST /deliverable/commit is called explicitly.
            committed = (
                verify_session.query(DeliverableVersion)
                .filter(DeliverableVersion.pile_id == pile_id)
                .count()
            )
            assert committed == 0

            final_run = verify_session.get(Run, run_id)
            assert final_run.current_stage == "completed"
        finally:
            verify_session.close()

        final_snapshot = graph.get_state(config)
        assert final_snapshot.next == ()
    finally:
        _clear_checkpoints(str(run_id))
