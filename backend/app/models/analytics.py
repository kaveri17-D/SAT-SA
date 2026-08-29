import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text, JSON, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import Base, GUID, TimestampMixin
from app.models.enums import FindingSeverity, FindingStatus, QueueItemStatus


class Finding(Base, TimestampMixin):
    __tablename__ = "findings"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    analysis_run_id = Column(GUID, ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_id = Column(String(100), nullable=True, index=True)
    rule_version = Column(String(50), nullable=False, default="1.0.0")
    model_version = Column(String(50), nullable=True)
    
    cse_id = Column(GUID, ForeignKey("cses.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(GUID, ForeignKey("assets.id", ondelete="CASCADE"), nullable=True, index=True)
    case_id = Column(GUID, ForeignKey("cases.id", ondelete="SET NULL"), nullable=True, index=True)
    
    severity = Column(Enum(FindingSeverity, native_enum=False), nullable=False, default=FindingSeverity.MEDIUM, index=True)
    
    # Supervisory Metrics & Evidence Quality
    anomaly_score = Column(Float, nullable=False, default=0.0)
    confidence = Column(Float, nullable=False, default=1.0)
    risk_score = Column(Float, nullable=False, default=0.0)
    supervisory_priority = Column(Float, nullable=False, default=0.0, index=True)
    evidence_completeness = Column(Float, nullable=False, default=100.0)  # 0.0 to 100.0%
    
    # Explainability Fields (Section 25)
    reason = Column(Text, nullable=False)
    expected_behaviour = Column(Text, nullable=False)
    observed_behaviour = Column(Text, nullable=False)
    evidence_refs = Column(JSON, nullable=False)  # JSON array of evidence reference dicts
    recommendation = Column(Text, nullable=False)
    
    status = Column(Enum(FindingStatus, native_enum=False), nullable=False, default=FindingStatus.NEW, index=True)

    # Relationships
    analysis_run = relationship("AnalysisRun", back_populates="findings")
    cse = relationship("CSE", back_populates="findings")
    asset = relationship("Asset", back_populates="findings")
    case = relationship("Case", back_populates="findings")
    evidence_records = relationship("Evidence", back_populates="finding", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_finding_cse_status", "cse_id", "status"),
        Index("idx_finding_cse_severity", "cse_id", "severity"),
        Index("idx_finding_priority", "supervisory_priority"),
        Index("idx_finding_run_cse", "analysis_run_id", "cse_id"),
        Index("idx_finding_run_rule", "analysis_run_id", "rule_id"),
    )



class Evidence(Base, TimestampMixin):
    __tablename__ = "evidence"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    finding_id = Column(GUID, ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    evidence_type = Column(String(100), nullable=False, index=True)
    source_table = Column(String(100), nullable=False)
    source_record_id = Column(String(255), nullable=False)
    evidence_timestamp = Column(DateTime(timezone=True), nullable=True, index=True)
    description = Column(Text, nullable=False)
    relevance = Column(String(50), nullable=False, default="HIGH")  # HIGH, CRITICAL, BASELINE_REFERENCE, SUPPRESSION_CONTEXT, MISSING_STEP
    payload_json = Column(JSON, nullable=True)
    provenance_json = Column(JSON, nullable=True)
    captured_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    finding = relationship("Finding", back_populates="evidence_records")


class RiskScore(Base, TimestampMixin):
    __tablename__ = "risk_scores"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    cse_id = Column(GUID, ForeignKey("cses.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_run_id = Column(GUID, ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    computed_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    
    total_score = Column(Float, nullable=False, default=0.0, index=True)
    raw_score = Column(Float, nullable=False, default=0.0)
    normalized_score = Column(Float, nullable=False, default=0.0)
    risk_band = Column(String(50), nullable=False, default="LOW", index=True)
    overall_confidence = Column(Float, nullable=False, default=1.0)
    
    component_breakdown = Column(JSON, nullable=False)  # {execution_gap, negative_space, peer_deviation, inv_anomaly, asset_criticality}
    contributing_finding_ids = Column(JSON, nullable=True)  # List of finding UUID strings
    explanation_json = Column(JSON, nullable=True)  # Structured "Why this score?" breakdown
    provenance_json = Column(JSON, nullable=True)
    
    rule_version = Column(String(50), nullable=False, default="1.0.0")
    model_version = Column(String(50), nullable=False, default="1.0.0")

    # Relationships
    cse = relationship("CSE", back_populates="risk_scores")
    analysis_run = relationship("AnalysisRun", back_populates="risk_scores")


class PeerGroup(Base, TimestampMixin):
    __tablename__ = "peer_groups"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    grouping_criteria = Column(JSON, nullable=False)

    # Relationships
    memberships = relationship("PeerGroupMembership", back_populates="peer_group", cascade="all, delete-orphan")
    benchmarks = relationship("Benchmark", back_populates="peer_group", cascade="all, delete-orphan")


class PeerGroupMembership(Base, TimestampMixin):
    __tablename__ = "peer_group_memberships"

    cse_id = Column(GUID, ForeignKey("cses.id", ondelete="CASCADE"), primary_key=True)
    peer_group_id = Column(GUID, ForeignKey("peer_groups.id", ondelete="CASCADE"), primary_key=True)
    joined_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    cse = relationship("CSE", back_populates="peer_memberships")
    peer_group = relationship("PeerGroup", back_populates="memberships")


class Benchmark(Base, TimestampMixin):
    __tablename__ = "benchmarks"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    peer_group_id = Column(GUID, ForeignKey("peer_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    metric_name = Column(String(100), nullable=False, index=True)
    median = Column(Float, nullable=False)
    p25 = Column(Float, nullable=False)
    p75 = Column(Float, nullable=False)
    std_dev = Column(Float, nullable=False)
    computed_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    peer_group = relationship("PeerGroup", back_populates="benchmarks")

    __table_args__ = (
        UniqueConstraint("peer_group_id", "metric_name", name="uq_peer_metric"),
    )


class ReviewQueueItem(Base, TimestampMixin):
    __tablename__ = "review_queue_items"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    analysis_run_id = Column(GUID, ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    finding_id = Column(GUID, ForeignKey("findings.id", ondelete="CASCADE"), nullable=False, index=True)
    cse_id = Column(GUID, ForeignKey("cses.id", ondelete="CASCADE"), nullable=False, index=True)
    risk_score_id = Column(GUID, ForeignKey("risk_scores.id", ondelete="SET NULL"), nullable=True, index=True)

    priority_score = Column(Float, nullable=False, index=True)
    rank = Column(Integer, nullable=False, index=True)
    priority_band = Column(String(50), nullable=False, index=True)

    rationale = Column(Text, nullable=False)
    contributing_factors = Column(JSON, nullable=False)
    explanation_json = Column(JSON, nullable=False)
    diversity_notes = Column(String(255), nullable=True)

    status = Column(Enum(QueueItemStatus, native_enum=False), nullable=False, default=QueueItemStatus.NEW, index=True)
    provenance_json = Column(JSON, nullable=True)

    # Relationships
    finding = relationship("Finding")
    cse = relationship("CSE")
    analysis_run = relationship("AnalysisRun")

    __table_args__ = (
        Index("idx_review_queue_run_rank", "analysis_run_id", "rank"),
    )

