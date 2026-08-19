import uuid
from pathlib import Path

from app.db.models import Conflict, Document, Fact, Run
from app.db.session import SessionLocal
from app.graph.build_graph import get_checkpointer, get_graph
from app.storage.local_fs import LocalFileStorage

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "samples"


def _make_document(session, pile, filename, doc_type="contract"):
    content = (SAMPLES_DIR / filename).read_bytes()
    storage = LocalFileStorage(pile_id=str(pile.id))
    storage_path = storage.save(content, ext="txt")

    document = Document(
        pile_id=pile.id,
        doc_type=doc_type,
        storage_path=storage_path,
        content_hash=f"test-{uuid.uuid4().hex}",
        original_filename=filename,
        mime_type="text/plain",
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


def _make_run(session, pile):
    run = Run(pile_id=pile.id, current_stage="extract")
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def _clear_checkpoints(thread_id: str) -> None:
    checkpointer = get_checkpointer()
    with checkpointer.conn.connection() as conn:
        conn.execute("DELETE FROM checkpoint_writes WHERE thread_id = %s", (thread_id,))
        conn.execute("DELETE FROM checkpoint_blobs WHERE thread_id = %s", (thread_id,))
        conn.execute("DELETE FROM checkpoints WHERE thread_id = %s", (thread_id,))


def test_resume_after_interruption_between_extract_and_conflicts(real_pile):
    session = SessionLocal()
    try:
        # The seeded contract/amendment pair disagrees on payment_term_days
        # (45 vs 60), which is exactly what detect_conflicts should catch
        # once it finally runs.
        doc_a = _make_document(session, real_pile, "01_Contract_MSA_PO4471.txt")
        doc_b = _make_document(session, real_pile, "02_Amendment1_MSA_PO4471.txt", doc_type="amendment")
        run = _make_run(session, real_pile)
        doc_a_id, doc_b_id, run_id = doc_a.id, doc_b.id, run.id
    finally:
        session.close()

    graph = get_graph()
    config = {"configurable": {"thread_id": str(run_id)}}
    initial_state = {
        "pile_id": str(real_pile.id),
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
        # Simulate the process being killed right after extraction finishes
        # but before conflict detection runs. interrupt_after halts
        # execution at exactly the checkpoint boundary LangGraph persists —
        # equivalent, for this purpose, to a real crash at that point.
        graph.invoke(initial_state, config, interrupt_after=["extract"])

        verify_session = SessionLocal()
        try:
            facts_after_extract = (
                verify_session.query(Fact)
                .filter(Fact.document_id.in_([doc_a_id, doc_b_id]))
                .count()
            )
            assert facts_after_extract > 0

            conflicts_after_extract = (
                verify_session.query(Conflict).filter(Conflict.pile_id == real_pile.id).count()
            )
            assert conflicts_after_extract == 0  # detect_conflicts has not run yet
        finally:
            verify_session.close()

        snapshot = graph.get_state(config)
        assert snapshot.next == ("detect_conflicts",)

        # Resume: passing None as input tells LangGraph to continue from
        # the last checkpoint instead of starting a fresh run.
        graph.invoke(None, config)

        verify_session = SessionLocal()
        try:
            facts_after_resume = (
                verify_session.query(Fact)
                .filter(Fact.document_id.in_([doc_a_id, doc_b_id]))
                .count()
            )
            assert facts_after_resume == facts_after_extract  # extraction was not re-run/duplicated

            conflicts_after_resume = (
                verify_session.query(Conflict).filter(Conflict.pile_id == real_pile.id).count()
            )
            assert conflicts_after_resume == 1  # conflict detection did complete on resume

            final_run = verify_session.get(Run, run_id)
            assert final_run.current_stage == "completed"
        finally:
            verify_session.close()

        final_snapshot = graph.get_state(config)
        assert final_snapshot.next == ()
        assert final_snapshot.values["current_stage"] == "completed"
    finally:
        _clear_checkpoints(str(run_id))
