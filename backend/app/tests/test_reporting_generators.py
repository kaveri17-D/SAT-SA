"""Tests for SAT-SA Report Generators across all 5 report types."""
import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.models import (
    CSE, Asset, Alert, Finding, RiskScore, Evidence, AnalysisRun,
    DatasetImport, AssetCriticality, AlertSeverity, FindingSeverity,
    FindingStatus, ReportType
)
from app.reporting.generators.executive_generator import ExecutiveReportGenerator
from app.reporting.generators.technical_generator import TechnicalReportGenerator
from app.reporting.generators.risk_generator import RiskReportGenerator
from app.reporting.generators.asset_generator import AssetReportGenerator
from app.reporting.generators.threat_intel_generator import ThreatIntelligenceReportGenerator


@pytest.fixture
def seeded_assessment(db: Session):
    # Create Import & Run
    ds = DatasetImport(
        filename="test_dataset.json",
        source="TEST_SYSTEM",
        imported_by="TEST_USER",
        row_count=100
    )
    db.add(ds)
    db.flush()

    run = AnalysisRun(
        dataset_import_id=ds.id,
        records_processed=100,
        findings_generated=5,
        rule_version="1.0.0",
        model_version="1.0.0"
    )
    db.add(run)
    db.flush()

    # Create CSE & Asset
    cse = CSE(
        name=f"TEST_CSE_{uuid.uuid4().hex[:6]}",
        sector="ENERGY",
        entity_type="POWER_GRID",
        size_tier="TIER_1"
    )
    db.add(cse)
    db.flush()

    asset = Asset(
        cse_id=cse.id,
        name="POWER_GATEWAY_01",
        asset_type="APPLICATION_GATEWAY",
        criticality=AssetCriticality.CRITICAL
    )
    db.add(asset)
    db.flush()

    # Create Findings
    f1 = Finding(
        analysis_run_id=run.id,
        cse_id=cse.id,
        asset_id=asset.id,
        rule_id="GAP-01",
        severity=FindingSeverity.CRITICAL,
        anomaly_score=0.92,
        confidence=0.95,
        supervisory_priority=9.5,
        reason="Uninvestigated alert on critical energy gateway.",
        expected_behaviour="Triage within 15 minutes.",
        observed_behaviour="Alert unreviewed for 72 hours.",
        recommendation="Immediate review and escalation.",
        status=FindingStatus.NEW,
        evidence_refs=[{"source": "alerts", "id": "ALT-001"}]
    )
    db.add(f1)
    db.flush()

    # Create Evidence
    ev1 = Evidence(
        finding_id=f1.id,
        evidence_type="TELEMETRY_GAP",
        source_table="alerts",
        source_record_id="ALT-001",
        description="Critical alert unreviewed during active vulnerability window.",
        relevance="CRITICAL"
    )
    db.add(ev1)

    # Create RiskScore
    risk = RiskScore(
        cse_id=cse.id,
        analysis_run_id=run.id,
        total_score=78.5,
        raw_score=78.5,
        normalized_score=78.5,
        risk_band="HIGH",
        overall_confidence=0.95,
        component_breakdown={
            "execution_gap": 45.0,
            "negative_space": 20.0,
            "peer_deviation": 5.0,
            "investigation_anomaly": 8.5,
            "asset_criticality": 30.0
        }
    )
    db.add(risk)
    db.commit()
    db.refresh(run)
    db.refresh(cse)
    return {"run": run, "cse": cse, "asset": asset, "finding": f1, "risk": risk}


def test_executive_report_generation(db: Session, seeded_assessment):
    run = seeded_assessment["run"]
    cse = seeded_assessment["cse"]

    gen = ExecutiveReportGenerator(db, run, cse)
    res = gen.generate("REP-TEST-001")

    assert "summary" in res
    assert "content" in res
    assert res["summary"]["overall_risk_score"] == 78.5
    assert res["summary"]["critical_findings"] >= 1
    assert "executive_summary" in res["content"]
    assert "top_security_gaps" in res["content"]
    assert len(res["content"]["top_security_gaps"]) >= 1


def test_technical_report_generation(db: Session, seeded_assessment):
    run = seeded_assessment["run"]
    cse = seeded_assessment["cse"]

    gen = TechnicalReportGenerator(db, run, cse)
    res = gen.generate("REP-TEST-002")

    assert res["summary"]["total_findings"] >= 1
    assert len(res["content"]["detailed_findings"]) >= 1
    finding_data = res["content"]["detailed_findings"][0]
    assert finding_data["rule_id"] == "GAP-01"
    assert finding_data["severity"] == "CRITICAL"
    assert len(finding_data["evidence_records"]) >= 1


def test_risk_report_generation(db: Session, seeded_assessment):
    run = seeded_assessment["run"]
    cse = seeded_assessment["cse"]

    gen = RiskReportGenerator(db, run, cse)
    res = gen.generate("REP-TEST-003")

    assert res["summary"]["overall_risk_score"] == 78.5
    assert "five_component_decomposition" in res["content"]
    decomp = res["content"]["five_component_decomposition"]
    assert "R1_execution_gap" in decomp
    assert "R2_negative_space" in decomp
    assert "R5_asset_criticality" in decomp


def test_asset_report_generation(db: Session, seeded_assessment):
    run = seeded_assessment["run"]
    cse = seeded_assessment["cse"]

    gen = AssetReportGenerator(db, run, cse)
    res = gen.generate("REP-TEST-004")

    assert res["summary"]["total_assets"] >= 1
    assert len(res["content"]["asset_inventory"]) >= 1
    asset_entry = res["content"]["asset_inventory"][0]
    assert asset_entry["name"] == "POWER_GATEWAY_01"
    assert asset_entry["criticality"] == "CRITICAL"


def test_threat_intel_report_generation(db: Session, seeded_assessment):
    run = seeded_assessment["run"]
    cse = seeded_assessment["cse"]

    gen = ThreatIntelligenceReportGenerator(db, run, cse)
    res = gen.generate("REP-TEST-005")

    assert "mitre_attack_matrix_coverage" in res["content"]
    assert "provenance_and_authoritative_sources" in res["content"]
    assert len(res["content"]["provenance_and_authoritative_sources"]) == 3
