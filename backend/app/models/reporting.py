import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, JSON, Index, Boolean
from sqlalchemy.orm import relationship
from app.models.base import Base, GUID, TimestampMixin
from app.models.enums import ReportType, ReportStatus


class ReportSnapshot(Base, TimestampMixin):
    __tablename__ = "report_snapshots"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    report_number = Column(String(50), nullable=False, unique=True, index=True)
    report_type = Column(Enum(ReportType, native_enum=False), nullable=False, index=True)
    status = Column(Enum(ReportStatus, native_enum=False), nullable=False, default=ReportStatus.COMPLETED, index=True)
    
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    analysis_run_id = Column(GUID, ForeignKey('analysis_runs.id', ondelete='CASCADE'), nullable=False, index=True)
    cse_id = Column(GUID, ForeignKey('cses.id', ondelete='SET NULL'), nullable=True, index=True)
    
    generated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    generated_by = Column(String(100), nullable=False, default='SYSTEM_EXAMINER', index=True)
    
    schema_version = Column(String(50), nullable=False, default='1.0.0')
    system_version = Column(String(50), nullable=False, default='1.0.0')
    data_foundation_version = Column(String(50), nullable=False, default='1.0.0')
    
    sha256_checksum = Column(String(64), nullable=False, index=True)
    is_tampered = Column(Boolean, nullable=False, default=False)
    
    summary_json = Column(JSON, nullable=False)
    content_json = Column(JSON, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    
    # Relationships
    analysis_run = relationship('AnalysisRun')
    cse = relationship('CSE')
    evidence_refs = relationship('ReportEvidenceReference', back_populates='report', cascade='all, delete-orphan')

    __table_args__ = (
        Index('idx_report_run_type', 'analysis_run_id', 'report_type'),
        Index('idx_report_cse_date', 'cse_id', 'generated_at'),
    )


class ReportEvidenceReference(Base, TimestampMixin):
    __tablename__ = "report_evidence_references"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    report_id = Column(GUID, ForeignKey('report_snapshots.id', ondelete='CASCADE'), nullable=False, index=True)
    finding_id = Column(GUID, ForeignKey('findings.id', ondelete='SET NULL'), nullable=True, index=True)
    evidence_id = Column(GUID, ForeignKey('evidence.id', ondelete='SET NULL'), nullable=True, index=True)
    
    evidence_type = Column(String(100), nullable=False, index=True)
    source_table = Column(String(100), nullable=False)
    source_record_id = Column(String(255), nullable=False)
    relevance = Column(String(50), nullable=False, default='HIGH')
    
    description = Column(Text, nullable=False)
    provenance_json = Column(JSON, nullable=True)

    # Relationships
    report = relationship('ReportSnapshot', back_populates='evidence_refs')
    finding = relationship('Finding')
    evidence = relationship('Evidence')
