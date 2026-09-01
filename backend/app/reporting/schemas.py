"""Schemas and DTOs for SAT-SA Reporting System."""
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.models.enums import ReportType, ReportStatus, ExportFormat


class ReportGenerateRequest(BaseModel):
    assessment_id: str = Field(..., description="Target AnalysisRun UUID")
    report_type: ReportType = Field(ReportType.EXECUTIVE, description="Type of report to generate")
    cse_id: Optional[str] = Field(None, description="Optional CSE UUID to scope the report")
    title: Optional[str] = Field(None, description="Custom report title")
    description: Optional[str] = Field(None, description="Custom report description")
    generated_by: Optional[str] = Field("EXAMINER_NCIIPC", description="Examiner/Analyst handle")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")


class ReportSummaryDTO(BaseModel):
    id: str
    report_number: str
    report_type: str
    status: str
    title: str
    assessment_id: str
    cse_id: Optional[str]
    cse_name: Optional[str]
    generated_at: str
    generated_by: str
    sha256_checksum: str
    is_tampered: bool
    summary: Dict[str, Any]


class ReportDetailDTO(ReportSummaryDTO):
    description: Optional[str]
    schema_version: str
    system_version: str
    data_foundation_version: str
    content: Dict[str, Any]
    metadata: Optional[Dict[str, Any]]
    evidence_references: List[Dict[str, Any]]
    tamper_verified: bool


class AuditEventRequest(BaseModel):
    user_id: str
    actor_role: str = "EXAMINER"
    action: str
    entity_type: str
    entity_id: str
    status: str = "SUCCESS"
    correlation_id: Optional[str] = None
    before_after: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class AuditLogDTO(BaseModel):
    id: str
    user_id: str
    actor_role: str
    action: str
    entity_type: str
    entity_id: str
    timestamp: str
    status: str
    correlation_id: Optional[str]
    before_after: Optional[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]]
    integrity_hash: Optional[str]
    previous_hash: Optional[str]


class AuditLogQueryFilter(BaseModel):
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    user_id: Optional[str] = None
    actor_role: Optional[str] = None
    action: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    status: Optional[str] = None
    correlation_id: Optional[str] = None
    limit: int = 50
    offset: int = 0


class AuditLogListResponse(BaseModel):
    total_count: int
    page_count: int
    page_size: int
    offset: int
    logs: List[AuditLogDTO]


class AuditVerificationResponse(BaseModel):
    is_valid: bool
    total_events: int
    verified_events: int
    tampered_event_id: Optional[str]
    details: str
