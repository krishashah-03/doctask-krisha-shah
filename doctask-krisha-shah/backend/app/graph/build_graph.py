import uuid

from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph
from psycopg_pool import ConnectionPool

from app.config import settings
from app.db.models import Run
from app.db.session import SessionLocal
from app.graph.nodes.detect_conflicts import detect_conflicts
from app.graph.nodes.examine_rules import examine_rules
from app.graph.nodes.extract import extract_document
from app.graph.nodes.generate_deliverable import generate_deliverable
from app.graph.state import PipelineState

_pool: ConnectionPool | None = None
_checkpointer: PostgresSaver | None = None
_graph: CompiledStateGraph | None = None


def get_checkpointer() -> PostgresSaver:
    """A process-wide Postgres-backed checkpointer, pointed at DATABASE_URL.

    LangGraph creates and manages its own checkpoint tables via .setup() —
    no changes to schema.sql are needed for this.
    """
    global _pool, _checkpointer
    if _checkpointer is None:
        _pool = ConnectionPool(
            conninfo=settings.DATABASE_URL,
            max_size=10,
            kwargs={"autocommit": True, "prepare_threshold": 0},
            open=True,
        )
        _checkpointer = PostgresSaver(_pool)
        _checkpointer.setup()
    return _checkpointer


def _set_run_stage(run_id: str, stage: str) -> None:
    db = SessionLocal()
    try:
        run = db.get(Run, uuid.UUID(run_id))
        if run is not None:
            run.current_stage = stage
            db.commit()
    finally:
        db.close()


def _extract_node(state: PipelineState) -> dict:
    _set_run_stage(state["run_id"], "extract")

    db = SessionLocal()
    try:
        created_fact_ids: list[str] = []
        for document_id in state["document_ids"]:
            outcome = extract_document(document_id=document_id, run_id=state["run_id"], db=db)
            created_fact_ids.extend(str(fact.id) for fact in outcome.facts)
    finally:
        db.close()

    _set_run_stage(state["run_id"], "extract_complete")
    return {"created_fact_ids": created_fact_ids, "current_stage": "extract_complete"}


def _detect_conflicts_node(state: PipelineState) -> dict:
    _set_run_stage(state["run_id"], "detect_conflicts")

    db = SessionLocal()
    try:
        outcome = detect_conflicts(pile_id=state["pile_id"], run_id=state["run_id"], db=db)
        created_conflict_ids = [str(conflict.id) for conflict in outcome.conflicts]
    finally:
        db.close()

    _set_run_stage(state["run_id"], "detect_conflicts_complete")
    return {"created_conflict_ids": created_conflict_ids, "current_stage": "detect_conflicts_complete"}


def _generate_deliverable_node(state: PipelineState) -> dict:
    _set_run_stage(state["run_id"], "generate_deliverable")

    db = SessionLocal()
    try:
        outcome = generate_deliverable(pile_id=state["pile_id"], run_id=state["run_id"], db=db)
    finally:
        db.close()

    _set_run_stage(state["run_id"], "generate_deliverable_complete")
    return {
        "draft_sections": outcome.sections,
        "draft_diff": outcome.diff,
        "current_stage": "generate_deliverable_complete",
    }


def _examine_rules_node(state: PipelineState) -> dict:
    _set_run_stage(state["run_id"], "examine_rules")

    db = SessionLocal()
    try:
        outcome = examine_rules(pile_id=state["pile_id"], run_id=state["run_id"], db=db)
        created_finding_ids = [str(finding.id) for finding in outcome.findings]
    finally:
        db.close()

    # The graph stops here on purpose — human review (approve/reject
    # conflicts and findings) happens outside the graph, and only the
    # explicit POST /piles/{pile_id}/deliverable/commit endpoint turns the
    # draft sitting in run_events into a real deliverable_versions row.
    _set_run_stage(state["run_id"], "completed")
    return {"created_finding_ids": created_finding_ids, "current_stage": "completed"}


def build_graph() -> CompiledStateGraph:
    builder = StateGraph(PipelineState)
    builder.add_node("extract", _extract_node)
    builder.add_node("detect_conflicts", _detect_conflicts_node)
    builder.add_node("generate_deliverable", _generate_deliverable_node)
    builder.add_node("examine_rules", _examine_rules_node)
    builder.set_entry_point("extract")
    builder.add_edge("extract", "detect_conflicts")
    builder.add_edge("detect_conflicts", "generate_deliverable")
    builder.add_edge("generate_deliverable", "examine_rules")
    builder.add_edge("examine_rules", END)
    return builder.compile(checkpointer=get_checkpointer())


def get_graph() -> CompiledStateGraph:
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
