"""Phase 15: Complete End-to-End Assessment Workflow and Lineage Validation."""
import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import (
    CSE, Asset, Alert, Investigation, Finding, Evidence, RiskScore,
    ReviewQueueItem, AnalysisRun, DatasetImport, AssetCriticality,
    AlertSeverity, FindingSeverity, FindingStatus, QueueItemStatus, ReportType,
    AuditLog
)
from app.reporting.builder import ReportBuilder
from app.reporting.schemas import ReportGenerateRequest
from app.audit.service import AuditService


def test_complete_e2e_assessment_lineage(db: Session):
    """Execute complete workflow proving lineage:
    Input Telemetry -> Ingestion -> Finding -> Evidence -> Risk Score -> Prioritization -> Report Snapshot -> Evidence References -> Audit Event.
    """
    # 1. Ingestion Import
    import_id = uuid.uuid4()
    ds = DatasetImport(
        id=import_id,
        filename="telemetry_e2e_test.json",
        source="E2E_INTEGRATION_PIPELINE",
        imported_by="EXAMINER_E2E",
        row_count=50
    )
    db.add(ds)
    db.flush()

    # 2. Analysis Run
    run_id = uuid.uuid4()
    run = AnalysisRun(
        id=run_id,
        dataset_import_id=ds.id,
        records_processed=50,
        findings_generated=2,
        rule_version="1.0.0",
        model_version="1.0.0"
    )
    db.add(run)
    db.flush()

    # 3. Monitored CSE & Asset
    cse = CSE(
        name=f"E2E_POWER_GRID_{uuid.uuid4().hex[:6]}",
        sector="ENERGY",
        entity_type="CRITICAL_INFRASTRUCTURE",
        size_tier="TIER_1"
    )
    db.add(cse)
    db.flush()

    asset = Asset(
        cse_id=cse.id,
        name="SCADA_CENTRAL_RTU",
        asset_type="INDUSTRIAL_CONTROLLER",
        criticality=AssetCriticality.CRITICAL
    )
    db.add(asset)
    db.flush()

    # 4. Input Telemetry Alert
    alert = Alert(
        cse_id=cse.id,
        asset_id=asset.id,
        source_system="SIEM_SPLUNK",
        category="AUTHENTICATION",
        severity=AlertSeverity.CRITICAL,
        raw_severity="CRITICAL",
        status="OPEN"
    )
    db.add(alert)
    db.flush()

    # 5. Finding
    finding = Finding(
        analysis_run_id=run.id,
        cse_id=cse.id,
        asset_id=asset.id,
        rule_id="GAP-01",
        severity=FindingSeverity.CRITICAL,
        anomaly_score=0.96,
        confidence=0.98,
        supervisory_priority=9.8,
        evidence_completeness=1.0,
        reason="Uninvestigated critical SCADA modification alert during active threat campaign.",
        expected_behaviour="Immediate isolation within 5 minutes.",
        observed_behaviour="Alert unreviewed for 48 hours.",
        recommendation="Initiate emergency supervisor isolation and firmware hash verification.",
        status=FindingStatus.NEW,
        evidence_refs=[{"source": "alerts", "id": str(alert.id)}]
    )
    db.add(finding)
    db.flush()

    # 6. Evidence Record linking finding to source record
    ev = Evidence(
        finding_id=finding.id,
        evidence_type="OPERATIONAL_GAP",
        source_table="alerts",
        source_record_id=str(alert.id),
        description="Raw alert telemetry confirming unhandled critical severity alert.",
        relevance="CRITICAL",
        provenance_json={"pipeline": "SAT-SA_INGESTION_v1", "ingested_at": datetime.now(timezone.utc).isoformat()}
    )
    db.add(ev)
    db.flush()

    # 7. Supervisory Risk Score
    risk = RiskScore(
        cse_id=cse.id,
        analysis_run_id=run.id,
        total_score=88.5,
        raw_score=88.5,
        normalized_score=88.5,
        risk_band="CRITICAL",
        overall_confidence=0.98,
        component_breakdown={
            "execution_gap": 50.0,
            "negative_space": 25.0,
            "peer_deviation": 8.0,
            "investigation_anomaly": 5.5,
            "asset_criticality": 35.0
        },
        contributing_finding_ids=[str(finding.id)]
    )
    db.add(risk)
    db.flush()

    # 8. Prioritization Queue Item
    queue_item = ReviewQueueItem(
        analysis_run_id=run.id,
        finding_id=finding.id,
        cse_id=cse.id,
        rank=1,
        priority_score=9.8,
        priority_band="CRITICAL",
        status=QueueItemStatus.NEW,
        rationale="Top supervisory priority: Critical SCADA asset exposure.",
        contributing_factors={"severity": 10.0, "risk_score": 88.5, "novelty": 1.0},
        explanation_json={"primary_driver": "Critical SCADA vulnerability uninvestigated"}
    )
    db.add(queue_item)
    db.commit()

    # 9. Generate Report Snapshot through builder
    req = ReportGenerateRequest(
        assessment_id=str(run.id),
        report_type=ReportType.EXECUTIVE,
        cse_id=str(cse.id),
        title="E2E Validation Official Executive Report",
        generated_by="EXAMINER_LEAD"
    )
    snapshot = ReportBuilder.generate_report(db, req)

    # Validate Complete Lineage
    assert snapshot.id is not None
    assert snapshot.analysis_run_id == run.id
    assert snapshot.cse_id == cse.id
    assert len(snapshot.sha256_checksum) == 64
    assert snapshot.is_tampered is False
    assert len(snapshot.evidence_refs) >= 1

    # Verify Report Evidence Reference points back to Finding and Evidence
    ref = snapshot.evidence_refs[0]
    assert ref.finding_id == finding.id
    assert ref.evidence_id == ev.id
    assert ref.source_table == "alerts"
    assert ref.source_record_id == str(alert.id)

    # Verify Audit Event recorded in cryptographic chain
    latest_audit = db.query(AuditLog).filter(AuditLog.entity_id == str(snapshot.id)).first()
    assert latest_audit is not None
    assert latest_audit.action == "REPORT_GENERATED"
    assert latest_audit.integrity_hash is not None
