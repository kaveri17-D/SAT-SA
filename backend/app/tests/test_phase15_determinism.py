"""Phase 15: Determinism and Analytical Repeatability Validation."""
import json
import uuid
import pytest
from sqlalchemy.orm import Session
from app.models import CSE, Asset, Finding, RiskScore, AnalysisRun, DatasetImport, AssetCriticality, FindingSeverity, FindingStatus, ReportType
from app.reporting.generators.executive_generator import ExecutiveReportGenerator


def test_deterministic_report_generation_equivalence(db: Session):
    """Verify that running identical assessment state twice generates 100% equivalent analytical content."""
    ds = DatasetImport(filename="det.json", source="DET", imported_by="U")
    db.add(ds)
    db.flush()
    run = AnalysisRun(dataset_import_id=ds.id)
    db.add(run)
    db.flush()
    cse = CSE(name="DET_CSE", sector="DEFENSE", entity_type="AGENCY", size_tier="TIER_1")
    db.add(cse)
    db.flush()
    asset = Asset(cse_id=cse.id, name="DEF_GATEWAY", asset_type="VPN_CONCENTRATOR", criticality=AssetCriticality.CRITICAL)
    db.add(asset)
    db.flush()
    f = Finding(
        analysis_run_id=run.id,
        cse_id=cse.id,
        asset_id=asset.id,
        rule_id="GAP-01",
        severity=FindingSeverity.HIGH,
        anomaly_score=0.90,
        confidence=0.95,
        supervisory_priority=9.0,
        reason="Sensor silence observed on perimeter VPN gateway.",
        expected_behaviour="Continuous heartbeat every 60 seconds.",
        observed_behaviour="Zero telemetry for 12 hours.",
        recommendation="Verify agent service status.",
        status=FindingStatus.NEW,
        evidence_refs=[{"source": "alerts", "id": "ALT-001"}]
    )
    db.add(f)
    risk = RiskScore(
        cse_id=cse.id,
        analysis_run_id=run.id,
        total_score=65.0,
        raw_score=65.0,
        normalized_score=65.0,
        risk_band="ELEVATED",
        component_breakdown={"execution_gap": 30.0, "negative_space": 20.0, "peer_deviation": 5.0, "investigation_anomaly": 5.0, "asset_criticality": 15.0}
    )
    db.add(risk)
    db.commit()

    # Generator 1
    gen1 = ExecutiveReportGenerator(db, run, cse)
    res1 = gen1.generate("REP-DET-001", "Deterministic Test Report")

    # Generator 2
    gen2 = ExecutiveReportGenerator(db, run, cse)
    res2 = gen2.generate("REP-DET-001", "Deterministic Test Report")

    # Analytical outputs must be identical
    assert res1["summary"] == res2["summary"]
    assert res1["content"]["executive_summary"] == res2["content"]["executive_summary"]
    assert res1["content"]["severity_distribution"] == res2["content"]["severity_distribution"]
    assert res1["content"]["top_security_gaps"] == res2["content"]["top_security_gaps"]
