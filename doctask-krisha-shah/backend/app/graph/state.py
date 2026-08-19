from typing import TypedDict


class PipelineState(TypedDict):
    pile_id: str
    run_id: str
    document_ids: list[str]
    current_stage: str
    created_fact_ids: list[str]
    created_conflict_ids: list[str]
    draft_sections: list[dict]
    draft_diff: list[dict]
    created_finding_ids: list[str]
