import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PileCreate(BaseModel):
    name: str
    domain: str
    owner_user_id: uuid.UUID | None = None


class PileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    domain: str
    owner_user_id: uuid.UUID | None
    created_at: datetime


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pile_id: uuid.UUID
    doc_type: str
    storage_path: str
    content_hash: str
    original_filename: str | None
    mime_type: str | None
    status: str
    ingested_at: datetime
    deduplicated: bool = False


class FactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pile_id: uuid.UUID
    document_id: uuid.UUID
    fact_key: str
    fact_value: str
    char_start: int | None
    char_end: int | None
    confidence: float | None
    superseded_by: uuid.UUID | None
    operation_id: str
    created_at: datetime


class InjectionFlagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    char_start: int | None
    char_end: int | None
    detected_text: str
    created_at: datetime


class ExtractionResponse(BaseModel):
    run_id: uuid.UUID
    facts: list[FactOut]
    injection_flags: list[InjectionFlagOut]


class ConflictOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pile_id: uuid.UUID
    fact_key: str
    fact_id_a: uuid.UUID
    fact_id_b: uuid.UUID
    description: str | None
    status: str
    run_id: uuid.UUID | None
    detected_at: datetime


class ConflictDetectionResponse(BaseModel):
    run_id: uuid.UUID
    conflicts: list[ConflictOut]


class DeliverableVersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pile_id: uuid.UUID
    version: int
    content: dict
    diff_from_prior: dict | list | None
    based_on_run_id: uuid.UUID | None
    created_at: datetime


class DeliverableCommitRequest(BaseModel):
    run_id: uuid.UUID


class RuleCreate(BaseModel):
    rule_key: str
    description: str
    rule_spec: dict | None = None


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pile_id: uuid.UUID
    rule_key: str
    description: str
    rule_spec: dict | None
    created_at: datetime


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pile_id: uuid.UUID
    rule_id: uuid.UUID | None
    document_id: uuid.UUID | None
    char_start: int | None
    char_end: int | None
    severity: str | None
    description: str
    status: str
    run_id: uuid.UUID | None
    created_at: datetime


class PendingReviewItem(BaseModel):
    item_type: str
    item_id: uuid.UUID
    pile_id: uuid.UUID
    description: str | None
    status: str
    detail: dict


class ReviewDecisionCreate(BaseModel):
    item_type: str
    item_id: uuid.UUID
    run_id: uuid.UUID | None = None
    decision: str
    decided_by: uuid.UUID


class ReviewDecisionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    item_type: str
    item_id: uuid.UUID
    run_id: uuid.UUID | None
    decision: str
    decided_by: uuid.UUID
    decided_at: datetime


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    pile_id: uuid.UUID
    status: str
    current_stage: str | None
    started_at: datetime
    completed_at: datetime | None
