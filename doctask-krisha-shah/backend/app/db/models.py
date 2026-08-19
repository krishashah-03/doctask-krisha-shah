from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import declarative_base
from pgvector.sqlalchemy import Vector

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    email = Column(Text, unique=True, nullable=False)
    display_name = Column(Text)
    role = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("role in ('reviewer', 'admin', 'service_account')", name="users_role_check"),
    )


class Pile(Base):
    __tablename__ = "piles"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name = Column(Text, nullable=False)
    domain = Column(Text, nullable=False)
    owner_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    pile_id = Column(UUID(as_uuid=True), ForeignKey("piles.id", ondelete="CASCADE"), nullable=False)
    doc_type = Column(Text, nullable=False)
    storage_path = Column(Text, nullable=False)
    content_hash = Column(Text, nullable=False)
    original_filename = Column(Text)
    mime_type = Column(Text)
    status = Column(Text, nullable=False, server_default="ingested")
    ingested_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "doc_type in ('contract', 'amendment', 'invoice', 'other')", name="documents_doc_type_check"
        ),
        CheckConstraint(
            "status in ('ingested', 'extracting', 'extracted', 'failed')", name="documents_status_check"
        ),
        UniqueConstraint("pile_id", "content_hash", name="documents_pile_id_content_hash_key"),
        Index("idx_documents_pile", "pile_id"),
    )


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    chunk_text = Column(Text, nullable=False)
    char_start = Column(Integer, nullable=False)
    char_end = Column(Integer, nullable=False)
    embedding = Column(Vector(1536))

    __table_args__ = (
        Index("idx_chunks_document", "document_id"),
        Index(
            "idx_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class Fact(Base):
    __tablename__ = "facts"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    pile_id = Column(UUID(as_uuid=True), ForeignKey("piles.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    fact_key = Column(Text, nullable=False)
    fact_value = Column(Text, nullable=False)
    char_start = Column(Integer)
    char_end = Column(Integer)
    confidence = Column(Numeric(4, 3))
    superseded_by = Column(UUID(as_uuid=True), ForeignKey("facts.id"))
    run_id = Column(UUID(as_uuid=True))
    operation_id = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("confidence between 0 and 1", name="facts_confidence_check"),
        UniqueConstraint("pile_id", "operation_id", name="facts_pile_id_operation_id_key"),
        Index("idx_facts_pile_key", "pile_id", "fact_key"),
    )


class Conflict(Base):
    __tablename__ = "conflicts"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    pile_id = Column(UUID(as_uuid=True), ForeignKey("piles.id", ondelete="CASCADE"), nullable=False)
    fact_key = Column(Text, nullable=False)
    fact_id_a = Column(UUID(as_uuid=True), ForeignKey("facts.id"), nullable=False)
    fact_id_b = Column(UUID(as_uuid=True), ForeignKey("facts.id"), nullable=False)
    description = Column(Text)
    status = Column(Text, nullable=False, server_default="pending")
    run_id = Column(UUID(as_uuid=True))
    detected_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("status in ('pending', 'approved', 'rejected')", name="conflicts_status_check"),
        Index("idx_conflicts_pile_status", "pile_id", "status"),
    )


class Rule(Base):
    __tablename__ = "rules"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    pile_id = Column(UUID(as_uuid=True), ForeignKey("piles.id", ondelete="CASCADE"), nullable=False)
    rule_key = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    rule_spec = Column(JSONB)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class Finding(Base):
    __tablename__ = "findings"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    pile_id = Column(UUID(as_uuid=True), ForeignKey("piles.id", ondelete="CASCADE"), nullable=False)
    rule_id = Column(UUID(as_uuid=True), ForeignKey("rules.id"))
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"))
    char_start = Column(Integer)
    char_end = Column(Integer)
    severity = Column(Text)
    description = Column(Text, nullable=False)
    status = Column(Text, nullable=False, server_default="pending")
    run_id = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("severity in ('low', 'medium', 'high')", name="findings_severity_check"),
        CheckConstraint("status in ('pending', 'approved', 'rejected')", name="findings_status_check"),
        Index("idx_findings_pile_status", "pile_id", "status"),
    )


class InjectionFlag(Base):
    __tablename__ = "injection_flags"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    document_id = Column(UUID(as_uuid=True), ForeignKey("documents.id"), nullable=False)
    char_start = Column(Integer)
    char_end = Column(Integer)
    detected_text = Column(Text, nullable=False)
    run_id = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class DeliverableVersion(Base):
    __tablename__ = "deliverable_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    pile_id = Column(UUID(as_uuid=True), ForeignKey("piles.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    content = Column(JSONB, nullable=False)
    diff_from_prior = Column(JSONB)
    based_on_run_id = Column(UUID(as_uuid=True))
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("pile_id", "version", name="deliverable_versions_pile_id_version_key"),
        Index("idx_deliverable_pile_version", "pile_id", version.desc()),
    )


class Run(Base):
    __tablename__ = "runs"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    pile_id = Column(UUID(as_uuid=True), ForeignKey("piles.id", ondelete="CASCADE"), nullable=False)
    status = Column(Text, nullable=False, server_default="running")
    current_stage = Column(Text)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    completed_at = Column(DateTime(timezone=True))

    __table_args__ = (
        CheckConstraint("status in ('running', 'completed', 'failed', 'killed')", name="runs_status_check"),
    )


class RunEvent(Base):
    __tablename__ = "run_events"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id", ondelete="CASCADE"), nullable=False)
    stage_name = Column(Text, nullable=False)
    seq = Column(Integer, nullable=False)
    payload = Column(JSONB)
    cost_usd = Column(Numeric(10, 4), server_default="0")
    duration_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("run_id", "stage_name", "seq", name="run_events_run_id_stage_name_seq_key"),
        Index("idx_run_events_run", "run_id"),
    )


class ReviewDecision(Base):
    __tablename__ = "review_decisions"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    item_type = Column(Text, nullable=False)
    item_id = Column(UUID(as_uuid=True), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey("runs.id"))
    decision = Column(Text, nullable=False)
    decided_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    decided_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint(
            "item_type in ('finding', 'conflict', 'deliverable_update')", name="review_decisions_item_type_check"
        ),
        CheckConstraint("decision in ('approved', 'rejected')", name="review_decisions_decision_check"),
        Index("idx_review_decisions_item", "item_type", "item_id"),
    )
