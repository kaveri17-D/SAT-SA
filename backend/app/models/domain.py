import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, JSON, Index, CheckConstraint
from sqlalchemy.orm import relationship
from app.models.base import Base, GUID, TimestampMixin
from app.models.enums import AssetCriticality, AlertSeverity, DispositionType


class CSE(Base, TimestampMixin):
    __tablename__ = "cses"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True, index=True)
    sector = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(100), nullable=False, index=True)
    size_tier = Column(String(50), nullable=False)  # TIER_1, TIER_2, TIER_3
    metadata_json = Column(JSON, nullable=True)

    # Relationships
    assets = relationship("Asset", back_populates="cse", cascade="all, delete-orphan")
    analysts = relationship("Analyst", back_populates="cse", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="cse", cascade="all, delete-orphan")
    cases = relationship("Case", back_populates="cse", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="cse", cascade="all, delete-orphan")
    risk_scores = relationship("RiskScore", back_populates="cse", cascade="all, delete-orphan")
    peer_memberships = relationship("PeerGroupMembership", back_populates="cse", cascade="all, delete-orphan")


class Asset(Base, TimestampMixin):
    __tablename__ = "assets"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    cse_id = Column(GUID, ForeignKey("cses.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    asset_type = Column(String(100), nullable=False)
    criticality = Column(Enum(AssetCriticality, native_enum=False), nullable=False, default=AssetCriticality.MEDIUM, index=True)
    status = Column(String(50), nullable=False, default="ACTIVE", index=True)
    decommissioned_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    cse = relationship("CSE", back_populates="assets")
    alerts = relationship("Alert", back_populates="asset", cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="asset")

    __table_args__ = (
        Index("idx_asset_cse_criticality", "cse_id", "criticality"),
    )


class Analyst(Base, TimestampMixin):
    __tablename__ = "analysts"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    cse_id = Column(GUID, ForeignKey("cses.id", ondelete="CASCADE"), nullable=False, index=True)
    handle = Column(String(100), nullable=False)
    role = Column(String(100), nullable=False, default="ANALYST_L1")

    # Relationships
    cse = relationship("CSE", back_populates="analysts")
    investigations = relationship("Investigation", back_populates="analyst")

    __table_args__ = (
        Index("idx_analyst_cse_handle", "cse_id", "handle", unique=True),
    )


class Alert(Base, TimestampMixin):
    __tablename__ = "alerts"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    cse_id = Column(GUID, ForeignKey("cses.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(GUID, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    source_system = Column(String(100), nullable=False)
    category = Column(String(100), nullable=False, index=True)
    severity = Column(Enum(AlertSeverity, native_enum=False), nullable=False, index=True)
    raw_severity = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="OPEN", index=True)

    # Relationships
    cse = relationship("CSE", back_populates="alerts")
    asset = relationship("Asset", back_populates="alerts")
    investigation = relationship("Investigation", back_populates="alert", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_alert_cse_severity_status", "cse_id", "severity", "status"),
        Index("idx_alert_created_at", "created_at"),
        Index("idx_alert_asset_created", "asset_id", "created_at"),
        Index("idx_alert_asset_category_created", "asset_id", "category", "created_at"),
        Index("idx_alert_cse_asset_created", "cse_id", "asset_id", "created_at"),
    )



class Investigation(Base, TimestampMixin):
    __tablename__ = "investigations"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    alert_id = Column(GUID, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    analyst_id = Column(GUID, ForeignKey("analysts.id", ondelete="SET NULL"), nullable=True, index=True)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)
    outcome = Column(String(100), nullable=True)

    # Relationships
    alert = relationship("Alert", back_populates="investigation")
    analyst = relationship("Analyst", back_populates="investigations")
    escalation = relationship("Escalation", back_populates="investigation", uselist=False, cascade="all, delete-orphan")


class Escalation(Base, TimestampMixin):
    __tablename__ = "escalations"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    investigation_id = Column(GUID, ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    escalated_to = Column(String(100), nullable=False)
    escalated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    reason = Column(Text, nullable=True)

    # Relationships
    investigation = relationship("Investigation", back_populates="escalation")


class Case(Base, TimestampMixin):
    __tablename__ = "cases"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    cse_id = Column(GUID, ForeignKey("cses.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="OPEN", index=True)
    opened_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    closed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    cse = relationship("CSE", back_populates="cases")
    closure = relationship("Closure", back_populates="case", uselist=False, cascade="all, delete-orphan")
    findings = relationship("Finding", back_populates="case")


class Closure(Base, TimestampMixin):
    __tablename__ = "closures"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    case_id = Column(GUID, ForeignKey("cases.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    disposition_type = Column(Enum(DispositionType, native_enum=False), nullable=False)
    closed_by = Column(String(100), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    justification = Column(Text, nullable=True)

    # Relationships
    case = relationship("Case", back_populates="closure")


class MaintenanceLog(Base, TimestampMixin):
    __tablename__ = "maintenance_logs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    cse_id = Column(GUID, ForeignKey("cses.id", ondelete="CASCADE"), nullable=False, index=True)
    asset_id = Column(GUID, ForeignKey("assets.id", ondelete="CASCADE"), nullable=True, index=True)
    maintenance_ref = Column(String(100), nullable=False)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    reason = Column(Text, nullable=True)
    approved_by = Column(String(100), nullable=True)

    # Relationships
    cse = relationship("CSE")
    asset = relationship("Asset")

