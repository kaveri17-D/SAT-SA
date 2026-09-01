"""Phase 15: All 5 Report Types E2E Generation, Verification, and Tamper Detection."""
import json
import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import (
    CSE, Asset, Finding, RiskScore, Evidence, AnalysisRun, DatasetImport,
    AssetCriticality, FindingSeverity, FindingStatus, ReportType
)
from app.reporting.builder import ReportBuilder
from app.reporting.snapshot import SnapshotManager
from app.reporting.schemas import ReportGenerateRequest
from app.reporting.exporters.json_exporter import JSONReportExporter
from app.reporting.exporters.html_exporter import HTMLReportExporter


@pytest.fixture
def assessment_context(db: Session):
    ds = DatasetImport(filename="rep_test.json", source="SYS", imported_by="U")
    db.add(ds)
    db.flush()
    run = AnalysisRun(dataset_import_id=ds.id)
    db.add(run)
    db.flush()
    cse = CSE(name=f"CSE_{uuid.uuid4().hex[:6]}", sector="FINANCE", entity_type="BANK", size_tier="TIER_1")
    db.add(cse)
    db.flush()
    asset = Asset(cse_id=cse.id, name="CORE_BANKING_SERVER", asset_type="DATABASE_SERVER", criticality=AssetCriticality.CRITICAL)
    db.add(asset)
    db.flush()
    f = Finding(
        analysis_run_id=run.id,
        cse_id=cse.id,
        asset_id=asset.id,
        rule_id="GAP-02",
        severity=FindingSeverity.HIGH,
        anomaly_score=0.85,
        confidence=0.90,
        supervisory_priority=8.5,
        reason="Premature closure of unauthorized privilege escalation investigation.",
        expected_behaviour="Complete forensic triage.",
        observed_behaviour="Closed in 30 seconds with no notes.",
        recommendation="Reopen and audit analyst action.",
        status=FindingStatus.NEW,
        evidence_refs=[{"source": "closures", "id": "CLO-101"}]
    )
    db.add(f)
    db.flush()
    ev = Evidence(finding_id=f.id, evidence_type="INVESTIGATION_ANOMALY", source_table="closures", source_record_id="CLO-101", description="Closure log")
    db.add(ev)
    db.flush()
    risk = RiskScore(
        cse_id=cse.id,
        analysis_run_id=run.id,
        total_score=72.0,
        raw_score=72.0,
        normalized_score=72.0,
        risk_band="HIGH",
        component_breakdown={"execution_gap": 40.0, "negative_space": 10.0, "peer_deviation": 12.0, "investigation_anomaly": 15.0, "asset_criticality": 25.0}
    )
    db.add(risk)
    db.commit()
    return {"run_id": str(run.id), "cse_id": str(cse.id)}


def test_all_five_report_generators_e2e(db: Session, assessment_context):
    run_id = assessment_context["run_id"]
    cse_id = assessment_context["cse_id"]

    for r_type in [
        ReportType.EXECUTIVE,
        ReportType.TECHNICAL,
        ReportType.RISK,
        ReportType.ASSET,
        ReportType.VULNERABILITY_THREAT_INTEL
    ]:
        req = ReportGenerateRequest(
            assessment_id=run_id,
            report_type=r_type,
            cse_id=cse_id,
            title=f"Official {r_type.value} E2E Report"
        )
        snap = ReportBuilder.generate_report(db, req)
        assert snap.id is not None
        assert snap.report_type == r_type
        assert len(snap.sha256_checksum) == 64
        assert snap.is_tampered is False

        # Verify HTML and JSON export
        json_out = JSONReportExporter.export(snap)
        assert json_out is not None
        assert "export_version" in json_out

        html_out = HTMLReportExporter.export(snap)
        assert html_out is not None
        assert "<!DOCTYPE html>" in html_out
        assert snap.report_number in html_out


def test_controlled_snapshot_tamper_detection(db: Session, assessment_context):
    run_id = assessment_context["run_id"]
    req = ReportGenerateRequest(
        assessment_id=run_id,
        report_type=ReportType.EXECUTIVE,
        title="Tamper Test Report"
    )
    snap = ReportBuilder.generate_report(db, req)
    
    # 1. Initial authentic check
    is_valid, msg = SnapshotManager.verify_integrity(snap)
    assert is_valid is True

    # 2. Tamper payload in DB
    snap.content_json = {"malicious_tamper": True, "executive_summary": {"narrative": "TAMPERED"}}
    db.commit()

    # 3. Check integrity on reload
    is_valid_after, msg_after = SnapshotManager.verify_integrity(snap)
    assert is_valid_after is False
    assert "Tamper detected" in msg_after
    assert snap.is_tampered is True
