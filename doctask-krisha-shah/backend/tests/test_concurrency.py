import threading
import uuid

from app.db.models import Conflict, DeliverableVersion, Document, Fact, Run
from app.db.session import SessionLocal
from app.graph.build_graph import get_checkpointer, get_graph
from app.graph.nodes.generate_deliverable import DeliverableCommitConflictError, commit_deliverable
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


def _run_pipeline_once(pile_id, document_ids, barrier=None):
    """Mirrors POST /piles/{pile_id}/run: create a Run row, invoke the
    graph over the given documents. `barrier`, if given, holds this thread
    until its twin is also ready, so the two runs' extract/detect_conflicts
    phases genuinely overlap instead of racing by accident of scheduling.
    """
    session = SessionLocal()
    try:
        run = Run(pile_id=pile_id, current_stage="extract")
        session.add(run)
        session.commit()
        session.refresh(run)
        run_id = run.id
    finally:
        session.close()

    if barrier is not None:
        barrier.wait(timeout=10)

    graph = get_graph()
    config = {"configurable": {"thread_id": str(run_id)}}
    initial_state = {
        "pile_id": str(pile_id),
        "run_id": str(run_id),
        "document_ids": [str(d) for d in document_ids],
        "current_stage": "extract",
        "created_fact_ids": [],
        "created_conflict_ids": [],
        "draft_sections": [],
        "draft_diff": [],
        "created_finding_ids": [],
    }
    graph.invoke(initial_state, config)
    return run_id


def test_two_concurrent_runs_on_same_pile_produce_no_duplicates(real_pile):
    setup_session = SessionLocal()
    try:
        # Same two documents processed by BOTH concurrent runs — this is
        # the actual race: two runs independently extracting and
        # conflict-checking the same pile at once.
        doc_a = _make_document_with_content(
            setup_session, real_pile, "Payment Terms: 45 days from invoice date.\n", "contract.txt"
        )
        doc_b = _make_document_with_content(
            setup_session, real_pile, "Payment Terms: 60 days from invoice date.\n", "amendment.txt"
        )
        pile_id, doc_a_id, doc_b_id = real_pile.id, doc_a.id, doc_b.id
    finally:
        setup_session.close()

    document_ids = [doc_a_id, doc_b_id]
    barrier = threading.Barrier(2)
    run_ids = {}
    errors = {}

    def _thread(key):
        try:
            run_ids[key] = _run_pipeline_once(pile_id, document_ids, barrier=barrier)
        except Exception as exc:  # noqa: BLE001 - surfaced via the assertion below
            errors[key] = exc

    thread_1 = threading.Thread(target=_thread, args=("run1",))
    thread_2 = threading.Thread(target=_thread, args=("run2",))
    thread_1.start()
    thread_2.start()
    thread_1.join(timeout=30)
    thread_2.join(timeout=30)

    try:
        assert not errors, f"pipeline runs raised: {errors}"

        verify_session = SessionLocal()
        try:
            facts = verify_session.query(Fact).filter(Fact.document_id.in_(document_ids)).all()
            fact_keys_seen = [(f.document_id, f.fact_key) for f in facts]
            assert len(fact_keys_seen) == len(set(fact_keys_seen)), f"duplicate facts: {fact_keys_seen}"

            conflicts = verify_session.query(Conflict).filter(Conflict.pile_id == pile_id).all()
            pairs_seen = [tuple(sorted((c.fact_id_a, c.fact_id_b))) for c in conflicts]
            assert len(pairs_seen) == len(set(pairs_seen)), f"duplicate conflicts: {pairs_seen}"
            assert len(conflicts) >= 1
        finally:
            verify_session.close()

        # Both runs drafted their own deliverable independently. Race their
        # commits against each other exactly like the Phase 1 test does.
        commit_barrier = threading.Barrier(2)
        commit_results = {}

        def _commit(key, run_id):
            session = SessionLocal()
            try:
                version_row = commit_deliverable(
                    pile_id=pile_id,
                    run_id=run_id,
                    db=session,
                    _on_after_read_version=lambda: commit_barrier.wait(timeout=10),
                )
                commit_results[key] = ("ok", version_row.version)
            except DeliverableCommitConflictError as exc:
                commit_results[key] = ("conflict", exc.version)
            finally:
                session.close()

        commit_thread_1 = threading.Thread(target=_commit, args=("c1", run_ids["run1"]))
        commit_thread_2 = threading.Thread(target=_commit, args=("c2", run_ids["run2"]))
        commit_thread_1.start()
        commit_thread_2.start()
        commit_thread_1.join(timeout=15)
        commit_thread_2.join(timeout=15)

        outcomes = [commit_results["c1"], commit_results["c2"]]
        successes = [o for o in outcomes if o[0] == "ok"]
        conflicts_outcome = [o for o in outcomes if o[0] == "conflict"]
        assert len(successes) == 1, f"expected exactly one commit success, got {outcomes}"
        assert len(conflicts_outcome) == 1, f"expected exactly one clean conflict, got {outcomes}"

        verify_session = SessionLocal()
        try:
            versions = [
                v.version
                for v in verify_session.query(DeliverableVersion)
                .filter(DeliverableVersion.pile_id == pile_id)
                .all()
            ]
            assert len(versions) == len(set(versions)), f"duplicate version numbers: {versions}"
            assert len(versions) == 1
        finally:
            verify_session.close()
    finally:
        for run_id in run_ids.values():
            _clear_checkpoints(str(run_id))
