"""Report Builder Orchestrator."""
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import uuid
from sqlalchemy.orm import Session
from app.models import AnalysisRun, CSE, ReportType, AnalysisRunStatus
from app.reporting.schemas import ReportGenerateRequest
from app.reporting.generators.executive_generator import ExecutiveReportGenerator
from app.reporting.generators.technical_generator import TechnicalReportGenerator
from app.reporting.generators.risk_generator import RiskReportGenerator
from app.reporting.generators.asset_generator import AssetReportGenerator
from app.reporting.generators.threat_intel_generator import ThreatIntelligenceReportGenerator
from app.reporting.snapshot import SnapshotManager
from app.audit.service import AuditService


class ReportBuilder:
    """Builds, signs, and snapshots assessment reports."""

    @staticmethod
    def generate_report(db: Session, request: ReportGenerateRequest) -> Any:
        run = None
        if request.assessment_id and request.assessment_id.lower() != "latest":
            try:
                run_uuid = uuid.UUID(request.assessment_id.strip())
                run = db.query(AnalysisRun).filter(AnalysisRun.id == run_uuid).first()
            except ValueError:
                pass
        if not run:
            run = (
                db.query(AnalysisRun)
                .filter(AnalysisRun.status == AnalysisRunStatus.COMPLETED, AnalysisRun.findings_generated > 0)
                .order_by(AnalysisRun.created_at.desc())
                .first()
            )
        if not run:
            run = db.query(AnalysisRun).order_by(AnalysisRun.created_at.desc()).first()
        if not run:
            raise ValueError("No AnalysisRun available for report generation.")

        cse = None
        if request.cse_id and request.cse_id.strip():
            try:
                cse = db.query(CSE).filter(CSE.id == uuid.UUID(request.cse_id.strip())).first()
            except ValueError:
                cse = None

        # Select generator
        if request.report_type == ReportType.EXECUTIVE:
            gen = ExecutiveReportGenerator(db, run, cse)
        elif request.report_type == ReportType.TECHNICAL:
            gen = TechnicalReportGenerator(db, run, cse)
        elif request.report_type == ReportType.RISK:
            gen = RiskReportGenerator(db, run, cse)
        elif request.report_type == ReportType.ASSET:
            gen = AssetReportGenerator(db, run, cse)
        elif request.report_type == ReportType.VULNERABILITY_THREAT_INTEL:
            gen = ThreatIntelligenceReportGenerator(db, run, cse)
        else:
            gen = ExecutiveReportGenerator(db, run, cse)

        report_num = f"REP-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        result = gen.generate(report_num, request.title)
        evidence_refs = gen.extract_evidence_references(gen.get_findings())

        snapshot = SnapshotManager.create_and_sign_snapshot(
            db=db,
            analysis_run_id=str(run.id),
            report_type=request.report_type,
            summary=result["summary"],
            content=result["content"],
            evidence_refs=evidence_refs,
            cse_id=str(cse.id) if cse else None,
            title=request.title,
            description=request.description,
            generated_by=request.generated_by or "EXAMINER_NCIIPC",
            metadata=request.metadata
        )

        # Audit event
        AuditService.log_event(
            db=db,
            user_id=request.generated_by or "EXAMINER_NCIIPC",
            action="REPORT_GENERATED",
            entity_type="REPORT_SNAPSHOT",
            entity_id=str(snapshot.id),
            actor_role="EXAMINER",
            status="SUCCESS",
            metadata={"report_number": snapshot.report_number, "report_type": snapshot.report_type.value}
        )

        return snapshot
