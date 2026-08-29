import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Enum, Float, ForeignKey, Integer, String, Text, JSON, Index, UniqueConstraint
from sqlalchemy.orm import relationship
from app.models.base import Base, GUID, TimestampMixin
from app.models.enums import AnalysisRunStatus, DatasetImportStatus, DataQualitySeverity, VersionStatus


class DatasetImport(Base, TimestampMixin):
    __tablename__ = "dataset_imports"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    filename = Column(String(255), nullable=False)
    source = Column(String(100), nullable=False)
    imported_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    imported_by = Column(String(100), nullable=False)
    row_count = Column(Integer, nullable=False, default=0)
    accepted_count = Column(Integer, nullable=False, default=0)
    quarantined_count = Column(Integer, nullable=False, default=0)
    status = Column(Enum(DatasetImportStatus, native_enum=False), nullable=False, default=DatasetImportStatus.PENDING, index=True)
    completeness_score = Column(Float, nullable=False, default=100.0)
    processing_duration_seconds = Column(Float, nullable=True)

    # Relationships
    quality_issues = relationship("DataQualityIssue", back_populates="dataset_import", cascade="all, delete-orphan")
    analysis_runs = relationship("AnalysisRun", back_populates="dataset_import", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="dataset_import")


class DataQualityIssue(Base, TimestampMixin):
    __tablename__ = "data_quality_issues"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    dataset_import_id = Column(GUID, ForeignKey("dataset_imports.id", ondelete="CASCADE"), nullable=False, index=True)
    issue_type = Column(String(100), nullable=False, index=True)
    field = Column(String(100), nullable=True)
    record_ref = Column(String(255), nullable=True)
    severity = Column(Enum(DataQualitySeverity, native_enum=False), nullable=False, default=DataQualitySeverity.MEDIUM, index=True)
    description = Column(Text, nullable=False)

    # Relationships
    dataset_import = relationship("DatasetImport", back_populates="quality_issues")


class RuleVersion(Base, TimestampMixin):
    __tablename__ = "rule_versions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    rule_id = Column(String(100), nullable=False, index=True)
    version = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    definition_json = Column(JSON, nullable=False)
    status = Column(Enum(VersionStatus, native_enum=False), nullable=False, default=VersionStatus.ACTIVE, index=True)
    created_by = Column(String(100), nullable=False, default="SYSTEM")

    # Relationships
    analysis_runs = relationship("AnalysisRun", back_populates="rule_version_ref")

    __table_args__ = (
        UniqueConstraint("rule_id", "version", name="uq_rule_version"),
    )


class ModelVersion(Base, TimestampMixin):
    __tablename__ = "model_versions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    model_name = Column(String(100), nullable=False, index=True)
    version = Column(String(50), nullable=False, index=True)
    trained_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    training_dataset_ref = Column(String(255), nullable=True)
    metrics_json = Column(JSON, nullable=True)
    status = Column(Enum(VersionStatus, native_enum=False), nullable=False, default=VersionStatus.ACTIVE, index=True)
    packaged_path = Column(String(512), nullable=True)

    # Relationships
    analysis_runs = relationship("AnalysisRun", back_populates="model_version_ref")

    __table_args__ = (
        UniqueConstraint("model_name", "version", name="uq_model_version"),
    )


class AnalysisRun(Base, TimestampMixin):
    __tablename__ = "analysis_runs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    dataset_import_id = Column(GUID, ForeignKey("dataset_imports.id", ondelete="CASCADE"), nullable=False, index=True)
    rule_version_id = Column(GUID, ForeignKey("rule_versions.id", ondelete="SET NULL"), nullable=True, index=True)
    model_version_id = Column(GUID, ForeignKey("model_versions.id", ondelete="SET NULL"), nullable=True, index=True)
    
    started_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(AnalysisRunStatus, native_enum=False), nullable=False, default=AnalysisRunStatus.PENDING, index=True)
    
    records_processed = Column(Integer, nullable=False, default=0)
    findings_generated = Column(Integer, nullable=False, default=0)
    
    rule_version = Column(String(50), nullable=False, default="1.0.0")
    model_version = Column(String(50), nullable=False, default="1.0.0")
    configuration = Column(JSON, nullable=True)
    processing_duration_seconds = Column(Float, nullable=True)

    # Relationships
    dataset_import = relationship("DatasetImport", back_populates="analysis_runs")
    rule_version_ref = relationship("RuleVersion", back_populates="analysis_runs")
    model_version_ref = relationship("ModelVersion", back_populates="analysis_runs")
    findings = relationship("Finding", back_populates="analysis_run", cascade="all, delete-orphan")
    risk_scores = relationship("RiskScore", back_populates="analysis_run", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="analysis_run")


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(String(100), nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False, index=True)
    entity_id = Column(String(255), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    before_after_json = Column(JSON, nullable=True)
    
    dataset_import_id = Column(GUID, ForeignKey("dataset_imports.id", ondelete="SET NULL"), nullable=True, index=True)
    analysis_run_id = Column(GUID, ForeignKey("analysis_runs.id", ondelete="SET NULL"), nullable=True, index=True)
    rule_version = Column(String(50), nullable=True)
    model_version = Column(String(50), nullable=True)

    # Relationships
    dataset_import = relationship("DatasetImport", back_populates="audit_logs")
    analysis_run = relationship("AnalysisRun", back_populates="audit_logs")
