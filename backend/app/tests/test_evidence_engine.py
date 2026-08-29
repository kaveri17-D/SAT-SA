import uuid
import time
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.models import (
    CSE, Asset, Alert, Investigation, Escalation, Case, Closure, MaintenanceLog,
    Finding, Evidence, AnalysisRun, DatasetImport, FindingSeverity, FindingStatus,
    AssetCriticality, AlertSeverity, DispositionType, DatasetImportStatus, AnalysisRunStatus
)
from app.evidence.reconstructor import OperationalWorkflowNode
from app.evidence.assembler import EvidenceAssembler, REQUIRED_EVIDENCE_CONTRACT
from app.evidence.schema import EvidenceType, EvidencePackage
from app.rules.evaluator import RuleEvaluationResult, EvaluationStatus
from app.main import app as fastapi_app


def clear_db(db: Session):
    db.query(Evidence).delete()
    db.query(Finding).delete()
    db.query(AnalysisRun).delete()
    db.query(MaintenanceLog).delete()
    db.query(Closure).delete()
    db.query(Case).delete()
    db.query(Escalation).delete()
    db.query(Investigation).delete()
    db.query(Alert).delete()
    db.query(Asset).delete()
    db.query(CSE).delete()
    db.query(DatasetImport).delete()
    db.commit()
    db.expire_all()


def test_execution_gap_evidence_assembly():
    """Test Execution Gap evidence assembly (GAP-01 workflow difference reconstruction)."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        now = datetime.now(timezone.utc)

        cse_id = uuid.uuid4()
        asset_id = uuid.uuid4()
        alert_id = uuid.uuid4()
        case_id = uuid.uuid4()

        cse = CSE(id=cse_id, name="Grid CSE", sector="ENERGY", entity_type="UTILITY", size_tier="TIER_1")
        asset = Asset(id=asset_id, cse_id=cse_id, name="Grid-Master-Node", asset_type="SCADA", criticality=AssetCriticality.CRITICAL)
        db.add_all([cse, asset])
        db.commit()

        alert = Alert(id=alert_id, cse_id=cse_id, asset_id=asset_id, source_system="SIEM", category="MALWARE_DETECTION", severity=AlertSeverity.HIGH, raw_severity="HIGH", created_at=now - timedelta(hours=2))
        inv = Investigation(id=uuid.uuid4(), alert_id=alert_id, started_at=now - timedelta(hours=1, minutes=50), duration_seconds=600)
        c = Case(id=case_id, cse_id=cse_id, opened_at=now - timedelta(hours=1, minutes=30))
        clo = Closure(id=uuid.uuid4(), case_id=case_id, disposition_type=DispositionType.FALSE_POSITIVE, closed_by="analyst_01", closed_at=now - timedelta(hours=1))
        db.add_all([alert, inv, c, clo])
        db.commit()

        node = OperationalWorkflowNode(alert=alert, asset=asset, cse=cse, investigation=inv, case=c, closure=clo)

        finding = Finding(
            id=uuid.uuid4(),
            analysis_run_id=uuid.uuid4(),
            rule_id="GAP-01",
            rule_version="1.0.0",
            cse_id=cse_id,
            asset_id=asset_id,
            case_id=case_id,
            severity=FindingSeverity.HIGH,
            anomaly_score=0.9,
            confidence=1.0,
            risk_score=75.0,
            supervisory_priority=75.0,
            reason="High severity alert closed without mandatory escalation.",
            expected_behaviour="Alert -> Investigation -> Escalation -> Case -> Closure",
            observed_behaviour="Alert -> Investigation -> Case -> Closure",
            evidence_refs=[],
            recommendation="Review analyst closure procedure.",
            status=FindingStatus.NEW
        )
        db.add(finding)
        db.commit()

        evidence_records = EvidenceAssembler.assemble_execution_gap_evidence(db, finding, node, completeness_score=98.0)
        assert len(evidence_records) >= 4

        # Verify Workflow Transition evidence item
        wf_ev = next(e for e in evidence_records if e.evidence_type == EvidenceType.WORKFLOW_TRANSITION.value)
        assert wf_ev.payload_json["expected_sequence"] == ["Alert", "Investigation", "Escalation", "Case", "Closure"]
        assert "Escalation" not in wf_ev.payload_json["observed_sequence"]
        assert len(wf_ev.payload_json["missing_transitions"]) >= 1

        # Verify Missing Escalation Record item
        miss_ev = next(e for e in evidence_records if e.evidence_type == EvidenceType.MISSING_EXPECTED_RECORD.value)
        assert miss_ev.payload_json["expected_evidence"] == "Escalation transition to L2/Supervisor"
        assert miss_ev.payload_json["data_quality_context"] == "Dataset completeness score is 98.0%"

    finally:
        db.close()


def test_negative_space_evidence_assembly():
    """Test Negative Space evidence assembly (NEG-01 missing expected telemetry)."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        now = datetime.now(timezone.utc)

        cse_id = uuid.uuid4()
        asset_id = uuid.uuid4()

        cse = CSE(id=cse_id, name="Telecom CSE", sector="TELECOM", entity_type="TELCO", size_tier="TIER_1")
        asset = Asset(id=asset_id, cse_id=cse_id, name="Core-Switch-1", asset_type="ROUTER", criticality=AssetCriticality.CRITICAL)
        db.add_all([cse, asset])
        db.commit()

        finding = Finding(
            id=uuid.uuid4(),
            analysis_run_id=uuid.uuid4(),
            rule_id="NEG-01",
            rule_version="1.0.0",
            cse_id=cse_id,
            asset_id=asset_id,
            severity=FindingSeverity.HIGH,
            anomaly_score=0.8,
            confidence=1.0,
            risk_score=70.0,
            supervisory_priority=70.0,
            reason="Telemetry silence of 120.0h exceeds 48.0h threshold.",
            expected_behaviour="Continuous telemetry required",
            observed_behaviour="Telemetry silence for 120.0h",
            evidence_refs=[],
            recommendation="Inspect core switch monitoring feed",
            status=FindingStatus.NEW
        )
        db.add(finding)
        db.commit()

        res = RuleEvaluationResult(
            rule_id="NEG-01",
            rule_version="1.0.0",
            status=EvaluationStatus.CONFIRMED,
            explanation="Telemetry silence of 120.0h exceeds 48.0h threshold.",
            expected_behaviour="Continuous telemetry",
            observed_behaviour="Silence duration of 120.0h",
            observed_activity="Telemetry silence duration 120.0h",
            recommendation="Inspect monitoring agent",
            target_entity_type="Asset",
            target_entity_id=str(asset_id),
            expected_window="48.0h",
            observed_window="120.0h"
        )

        evidence_records = EvidenceAssembler.assemble_negative_space_evidence(
            db=db, finding=finding, res=res, asset=asset, cse=cse, completeness_score=100.0
        )
        assert len(evidence_records) >= 3

        miss_ev = next(e for e in evidence_records if e.evidence_type == EvidenceType.MISSING_EXPECTED_RECORD.value)
        assert miss_ev.payload_json["expected_time_or_window"] == "At least 1 alert every 48.0 hours"
        assert miss_ev.payload_json["observed_evidence"] == "Telemetry silence duration 120.0h"
        assert "Zero telemetry records" in miss_ev.payload_json["reason_for_determining_absence"]

    finally:
        db.close()


def test_historical_baseline_and_peer_evidence():
    """Test HISTORICAL_BASELINE (NEG-02) and PEER_COMPARISON (NEG-04) payload formatting."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        now = datetime.now(timezone.utc)
        cse_id = uuid.uuid4()
        asset_id = uuid.uuid4()

        cse = CSE(id=cse_id, name="Bank CSE", sector="BANKING", entity_type="BANK", size_tier="TIER_1")
        asset = Asset(id=asset_id, cse_id=cse_id, name="ATM-Gateway", asset_type="GATEWAY", criticality=AssetCriticality.HIGH)
        db.add_all([cse, asset])
        db.commit()

        # 1. NEG-02 Baseline Test
        f_neg02 = Finding(
            id=uuid.uuid4(), analysis_run_id=uuid.uuid4(), rule_id="NEG-02", rule_version="1.0.0",
            cse_id=cse_id, severity=FindingSeverity.MEDIUM, anomaly_score=0.7, confidence=1.0, risk_score=50.0,
            supervisory_priority=50.0, reason="Drop", expected_behaviour="Normal", observed_behaviour="Drop",
            evidence_refs=[], recommendation="Investigate", status=FindingStatus.NEW
        )
        db.add(f_neg02)
        db.commit()

        res_neg02 = RuleEvaluationResult(
            rule_id="NEG-02", rule_version="1.0.0", status=EvaluationStatus.CONFIRMED,
            explanation="Drop", target_entity_type="CSE", target_entity_id=str(cse_id),
            baseline={"mean_daily_volume": 100.0, "std_dev": 10.0, "recent_24h_volume": 5.0, "drop_ratio_pct": 95.0, "z_score": -9.5},
            absence_deviation_measurement="Telemetry volume drop ratio of 95.00% (Z-Score: -9.50)"
        )
        ev_neg02 = EvidenceAssembler.assemble_negative_space_evidence(db, f_neg02, res_neg02, cse=cse)
        base_ev = next(e for e in ev_neg02 if e.evidence_type == EvidenceType.HISTORICAL_BASELINE.value)
        assert base_ev.payload_json["mean_daily_volume"] == 100.0
        assert base_ev.payload_json["drop_ratio_pct"] == 95.0

        # 2. NEG-04 Peer Test
        f_neg04 = Finding(
            id=uuid.uuid4(), analysis_run_id=uuid.uuid4(), rule_id="NEG-04", rule_version="1.0.0",
            cse_id=cse_id, asset_id=asset_id, severity=FindingSeverity.HIGH, anomaly_score=0.8, confidence=1.0, risk_score=60.0,
            supervisory_priority=60.0, reason="Peer ratio", expected_behaviour="Peer density", observed_behaviour="Under-monitored",
            evidence_refs=[], recommendation="Align logging", status=FindingStatus.NEW
        )
        db.add(f_neg04)
        db.commit()

        res_neg04 = RuleEvaluationResult(
            rule_id="NEG-04", rule_version="1.0.0", status=EvaluationStatus.CONFIRMED,
            explanation="Peer ratio", target_entity_type="Asset", target_entity_id=str(asset_id),
            baseline={"target_density": 5, "peer_median_density": 100, "density_ratio": 0.05, "peer_population": 4},
            absence_deviation_measurement="Asset alert density ratio is 0.05 (5.0% of peer median 100 alerts)"
        )
        ev_neg04 = EvidenceAssembler.assemble_negative_space_evidence(db, f_neg04, res_neg04, asset=asset)
        peer_ev = next(e for e in ev_neg04 if e.evidence_type == EvidenceType.PEER_COMPARISON.value)
        assert peer_ev.payload_json["peer_median_density"] == 100

    finally:
        db.close()


def test_evidence_completeness_and_confidence_adjustment():
    """Test evidence completeness calculation separate from confidence."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        now = datetime.now(timezone.utc)
        cse_id = uuid.uuid4()
        cse = CSE(id=cse_id, name="Energy CSE", sector="ENERGY", entity_type="UTILITY", size_tier="TIER_1")
        db.add(cse)
        db.commit()

        finding = Finding(
            id=uuid.uuid4(), analysis_run_id=uuid.uuid4(), rule_id="GAP-01", rule_version="1.0.0",
            cse_id=cse_id, severity=FindingSeverity.HIGH, anomaly_score=0.9, confidence=1.0, risk_score=75.0,
            supervisory_priority=75.0, reason="Gap", expected_behaviour="Exp", observed_behaviour="Obs",
            evidence_refs=[], recommendation="Rec", status=FindingStatus.NEW
        )
        db.add(finding)
        db.commit()

        # Add 2 out of 4 required evidence types (DIRECT_RECORD, DATA_QUALITY present, missing WORKFLOW_TRANSITION, MISSING_EXPECTED_RECORD)
        ev1 = Evidence(id=uuid.uuid4(), finding_id=finding.id, evidence_type=EvidenceType.DIRECT_RECORD.value, source_table="cses", source_record_id=str(cse_id), description="CSE record")
        ev2 = Evidence(id=uuid.uuid4(), finding_id=finding.id, evidence_type=EvidenceType.DATA_QUALITY.value, source_table="dataset_imports", source_record_id="REF", description="DQ record")
        db.add_all([ev1, ev2])
        db.commit()

        EvidenceAssembler._update_finding_evidence_completeness(finding, [ev1, ev2])
        
        # 2 out of 4 required types = 50.0% completeness
        assert finding.evidence_completeness == 50.0
        # Base confidence 1.0 scaled by 50.0% = 0.5
        assert finding.confidence == 0.5000

    finally:
        db.close()


def test_immutability_and_tamper_integrity():
    """Test EvidenceAssembler.verify_evidence_integrity flags deleted/modified canonical records."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        now = datetime.now(timezone.utc)

        cse_id = uuid.uuid4()
        asset_id = uuid.uuid4()

        cse = CSE(id=cse_id, name="Defense CSE", sector="DEFENCE", entity_type="MIL", size_tier="TIER_1")
        asset = Asset(id=asset_id, cse_id=cse_id, name="Radar-Unit-9", asset_type="RADAR", criticality=AssetCriticality.CRITICAL)
        db.add_all([cse, asset])
        db.commit()

        finding = Finding(
            id=uuid.uuid4(), analysis_run_id=uuid.uuid4(), rule_id="NEG-01", rule_version="1.0.0",
            cse_id=cse_id, asset_id=asset_id, severity=FindingSeverity.CRITICAL, anomaly_score=0.95, confidence=1.0, risk_score=90.0,
            supervisory_priority=90.0, reason="Silence", expected_behaviour="Telem", observed_behaviour="Silence",
            evidence_refs=[], recommendation="Inspect", status=FindingStatus.NEW
        )
        db.add(finding)
        db.commit()

        ev_asset = Evidence(
            id=uuid.uuid4(), finding_id=finding.id, evidence_type=EvidenceType.DIRECT_RECORD.value,
            source_table="assets", source_record_id=str(asset_id), description="Asset evidence"
        )
        db.add(ev_asset)
        db.commit()

        # 1. Clean verification pass
        v1 = EvidenceAssembler.verify_evidence_integrity(db, finding.id)
        assert v1["is_tampered"] is False

        # 2. Simulate canonical asset deletion from DB
        db.delete(asset)
        db.commit()

        v2 = EvidenceAssembler.verify_evidence_integrity(db, finding.id)
        assert v2["is_tampered"] is True
        assert len(v2["tampered_records"]) == 1

    finally:
        db.close()


def test_evidence_api_endpoints():
    """Test API read-only endpoints: GET /api/v1/evidence/{finding_id} and GET /api/v1/evidence/{finding_id}/verify."""
    client = TestClient(fastapi_app)
    db: Session = SessionLocal()
    try:
        clear_db(db)
        now = datetime.now(timezone.utc)
        cse_id = uuid.uuid4()
        cse = CSE(id=cse_id, name="API CSE", sector="BANKING", entity_type="BANK", size_tier="TIER_1")
        db.add(cse)
        db.commit()

        finding = Finding(
            id=uuid.uuid4(), analysis_run_id=uuid.uuid4(), rule_id="NEG-03", rule_version="1.0.0",
            cse_id=cse_id, severity=FindingSeverity.MEDIUM, anomaly_score=0.5, confidence=1.0, risk_score=40.0,
            supervisory_priority=40.0, reason="Missing category", expected_behaviour="Cat", observed_behaviour="None",
            evidence_refs=[], recommendation="Configure feed", status=FindingStatus.NEW
        )
        db.add(finding)
        db.commit()

        ev1 = Evidence(id=uuid.uuid4(), finding_id=finding.id, evidence_type=EvidenceType.DIRECT_RECORD.value, source_table="cses", source_record_id=str(cse_id), description="CSE")
        ev2 = Evidence(id=uuid.uuid4(), finding_id=finding.id, evidence_type=EvidenceType.MISSING_EXPECTED_RECORD.value, source_table="dataset_imports", source_record_id="REF", description="Cat missing")
        ev3 = Evidence(id=uuid.uuid4(), finding_id=finding.id, evidence_type=EvidenceType.DATA_QUALITY.value, source_table="dataset_imports", source_record_id="REF", description="DQ")
        db.add_all([ev1, ev2, ev3])
        db.commit()

        # Test GET /api/v1/evidence/{finding_id}
        res_pkg = client.get(f"/api/v1/evidence/{finding.id}")
        assert res_pkg.status_code == 200
        data = res_pkg.json()
        assert data["finding_id"] == str(finding.id)
        assert data["rule_id"] == "NEG-03"
        assert len(data["supporting_records"]) == 3

        # Test GET /api/v1/evidence/{finding_id}/verify
        res_ver = client.get(f"/api/v1/evidence/{finding.id}/verify")
        assert res_ver.status_code == 200
        ver_data = res_ver.json()
        assert ver_data["is_tampered"] is False

    finally:
        db.close()


def test_evidence_assembly_benchmark():
    """Benchmark EvidenceAssembler throughput across multiple findings."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        now = datetime.now(timezone.utc)

        cse_id = uuid.uuid4()
        asset_id = uuid.uuid4()
        cse = CSE(id=cse_id, name="Bench CSE", sector="ENERGY", entity_type="UTILITY", size_tier="TIER_1")
        asset = Asset(id=asset_id, cse_id=cse_id, name="Bench-Asset", asset_type="PUMP", criticality=AssetCriticality.HIGH)
        db.add_all([cse, asset])
        db.commit()

        # Create 100 synthetic findings
        findings = []
        for i in range(100):
            f = Finding(
                id=uuid.uuid4(), analysis_run_id=uuid.uuid4(), rule_id=f"GAP-0{i % 5 + 1}", rule_version="1.0.0",
                cse_id=cse_id, asset_id=asset_id, severity=FindingSeverity.HIGH, anomaly_score=0.8, confidence=1.0, risk_score=70.0,
                supervisory_priority=70.0, reason=f"Bench finding {i}", expected_behaviour="Exp", observed_behaviour="Obs",
                evidence_refs=[], recommendation="Rec", status=FindingStatus.NEW
            )
            findings.append(f)
        db.add_all(findings)
        db.commit()

        start_time = time.time()
        total_ev_records = 0
        node = OperationalWorkflowNode(alert=Alert(id=uuid.uuid4(), cse_id=cse_id, asset_id=asset_id, source_system="SIEM", category="MALWARE", severity=AlertSeverity.HIGH, raw_severity="HIGH", created_at=now), asset=asset, cse=cse)

        for f in findings:
            evs = EvidenceAssembler.assemble_execution_gap_evidence(db, f, node, completeness_score=100.0)
            total_ev_records += len(evs)

        duration = time.time() - start_time
        throughput = total_ev_records / duration if duration > 0 else 0.0

        assert duration >= 0.0
        assert total_ev_records >= 400

    finally:
        db.close()
