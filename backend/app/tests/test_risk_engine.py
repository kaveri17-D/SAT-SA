import uuid
import time
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.core.database import SessionLocal, Base, engine
from app.models import (
    CSE, Asset, Finding, AnalysisRun, RiskScore, FindingSeverity, FindingStatus,
    AssetCriticality, AnalysisRunStatus, DatasetImport, AuditLog, ReviewQueueItem
)
from app.analytics.risk_engine import SupervisoryRiskEngine, COMPONENT_CAPS, RISK_BAND_THRESHOLDS
from app.main import app as fastapi_app


def clear_db(db: Session):
    db.query(AuditLog).delete()
    db.query(ReviewQueueItem).delete()
    db.query(RiskScore).delete()
    db.query(Finding).delete()
    db.query(AnalysisRun).delete()
    db.query(Asset).delete()
    db.query(CSE).delete()
    db.query(DatasetImport).delete()
    db.commit()
    db.expire_all()


def test_scenario_a_single_execution_gap_finding():
    """Scenario A: Single execution-gap finding yields +30 contribution."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        cse_id = uuid.uuid4()
        run_id = uuid.uuid4()

        cse = CSE(id=cse_id, name="Grid CSE", sector="ENERGY", entity_type="POWER", size_tier="TIER_1")
        run = AnalysisRun(id=run_id, dataset_import_id=uuid.uuid4(), rule_version="1.0.0", model_version="1.0.0")
        db.add_all([cse, run])
        db.commit()

        f = Finding(
            id=uuid.uuid4(), analysis_run_id=run_id, rule_id="GAP-01", rule_version="1.0.0",
            cse_id=cse_id, severity=FindingSeverity.CRITICAL, anomaly_score=0.9, confidence=1.0, risk_score=30.0,
            supervisory_priority=30.0, reason="Critical gap", expected_behaviour="Escalate", observed_behaviour="Closed",
            evidence_refs=[], recommendation="Review", status=FindingStatus.NEW
        )
        db.add(f)
        db.commit()

        rs = SupervisoryRiskEngine.compute_cse_risk_score(db, cse_id, run_id)
        assert rs.component_breakdown["execution_gap"] == 30.0
        assert rs.normalized_score == 30.0
        assert rs.risk_band == "MODERATE"

    finally:
        db.close()


def test_scenario_b_single_negative_space_finding():
    """Scenario B: Single negative-space finding yields +25 contribution."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        cse_id = uuid.uuid4()
        run_id = uuid.uuid4()

        cse = CSE(id=cse_id, name="Telecom CSE", sector="TELECOM", entity_type="TELCO", size_tier="TIER_1")
        run = AnalysisRun(id=run_id, dataset_import_id=uuid.uuid4(), rule_version="1.0.0", model_version="1.0.0")
        db.add_all([cse, run])
        db.commit()

        f = Finding(
            id=uuid.uuid4(), analysis_run_id=run_id, rule_id="NEG-01", rule_version="1.0.0",
            cse_id=cse_id, severity=FindingSeverity.CRITICAL, anomaly_score=0.9, confidence=1.0, risk_score=25.0,
            supervisory_priority=25.0, reason="Silence", expected_behaviour="Telem", observed_behaviour="Silence",
            evidence_refs=[], recommendation="Inspect", status=FindingStatus.NEW
        )
        db.add(f)
        db.commit()

        rs = SupervisoryRiskEngine.compute_cse_risk_score(db, cse_id, run_id)
        assert rs.component_breakdown["negative_space"] == 25.0
        assert rs.normalized_score == 25.0
        assert rs.risk_band == "MODERATE"

    finally:
        db.close()


def test_scenario_c_multiple_finding_categories():
    """Scenario C: Multiple finding categories (+30 gap + 25 neg + 20 peer + 10 asset crit = 85 CRITICAL)."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        cse_id = uuid.uuid4()
        run_id = uuid.uuid4()

        cse = CSE(id=cse_id, name="Bank CSE", sector="BANKING", entity_type="BANK", size_tier="TIER_1")
        asset = Asset(id=uuid.uuid4(), cse_id=cse_id, name="Core-Vault", asset_type="SERVER", criticality=AssetCriticality.CRITICAL, status="ACTIVE")
        run = AnalysisRun(id=run_id, dataset_import_id=uuid.uuid4(), rule_version="1.0.0", model_version="1.0.0")
        db.add_all([cse, asset, run])
        db.commit()

        f_gap = Finding(id=uuid.uuid4(), analysis_run_id=run_id, rule_id="GAP-01", rule_version="1.0.0", cse_id=cse_id, severity=FindingSeverity.CRITICAL, confidence=1.0, reason="Gap", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW)
        f_neg = Finding(id=uuid.uuid4(), analysis_run_id=run_id, rule_id="NEG-01", rule_version="1.0.0", cse_id=cse_id, severity=FindingSeverity.CRITICAL, confidence=1.0, reason="Neg", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW)
        f_peer = Finding(id=uuid.uuid4(), analysis_run_id=run_id, rule_id="NEG-04", rule_version="1.0.0", cse_id=cse_id, severity=FindingSeverity.HIGH, confidence=1.0, reason="Peer", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW)

        db.add_all([f_gap, f_neg, f_peer])
        db.commit()

        rs = SupervisoryRiskEngine.compute_cse_risk_score(db, cse_id, run_id)
        assert rs.component_breakdown["execution_gap"] == 30.0
        assert rs.component_breakdown["negative_space"] == 25.0
        assert rs.component_breakdown["peer_deviation"] == 20.0
        assert rs.component_breakdown["asset_criticality"] == 10.0

        # Independent calculation verification
        expected_total = 30.0 + 25.0 + 20.0 + 10.0
        assert rs.normalized_score == expected_total == 85.0
        assert rs.risk_band == "CRITICAL"

    finally:
        db.close()


def test_scenario_d_score_max_100_clamping_safeguard():
    """Scenario D: Clamping safeguard ensures score <= 100.0."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        cse_id = uuid.uuid4()
        run_id = uuid.uuid4()

        cse = CSE(id=cse_id, name="Max CSE", sector="ENERGY", entity_type="POWER", size_tier="TIER_1")
        asset = Asset(id=uuid.uuid4(), cse_id=cse_id, name="Critical-Gen", asset_type="TURBINE", criticality=AssetCriticality.CRITICAL, status="ACTIVE")
        run = AnalysisRun(id=run_id, dataset_import_id=uuid.uuid4(), rule_version="1.0.0", model_version="1.0.0")
        db.add_all([cse, asset, run])
        db.commit()

        f_gap = Finding(id=uuid.uuid4(), analysis_run_id=run_id, rule_id="GAP-01", rule_version="1.0.0", cse_id=cse_id, severity=FindingSeverity.CRITICAL, confidence=1.0, reason="G", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW)
        f_neg = Finding(id=uuid.uuid4(), analysis_run_id=run_id, rule_id="NEG-01", rule_version="1.0.0", cse_id=cse_id, severity=FindingSeverity.CRITICAL, confidence=1.0, reason="N", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW)
        f_peer = Finding(id=uuid.uuid4(), analysis_run_id=run_id, rule_id="NEG-04", rule_version="1.0.0", cse_id=cse_id, severity=FindingSeverity.HIGH, confidence=1.0, reason="P", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW)
        f_inv = Finding(id=uuid.uuid4(), analysis_run_id=run_id, rule_id="GAP-02", rule_version="1.0.0", cse_id=cse_id, severity=FindingSeverity.HIGH, confidence=1.0, reason="I", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW)

        db.add_all([f_gap, f_neg, f_peer, f_inv])
        db.commit()

        # 30 + 25 + 20 + 15 + 10 = 100.0
        rs = SupervisoryRiskEngine.compute_cse_risk_score(db, cse_id, run_id)
        assert rs.raw_score == 100.0
        assert rs.normalized_score == 100.0
        assert rs.risk_band == "CRITICAL"

    finally:
        db.close()


def test_scenario_e_duplicate_root_cause_deduplication():
    """Scenario E: Duplicate findings from same root cause take max contribution, avoiding artificial inflation."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        cse_id = uuid.uuid4()
        run_id = uuid.uuid4()

        cse = CSE(id=cse_id, name="Dup CSE", sector="TELECOM", entity_type="TELCO", size_tier="TIER_1")
        run = AnalysisRun(id=run_id, dataset_import_id=uuid.uuid4(), rule_version="1.0.0", model_version="1.0.0")
        db.add_all([cse, run])
        db.commit()

        # 3 separate GAP-01 findings
        f1 = Finding(id=uuid.uuid4(), analysis_run_id=run_id, rule_id="GAP-01", rule_version="1.0.0", cse_id=cse_id, severity=FindingSeverity.MEDIUM, confidence=1.0, reason="Dup 1", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW)
        f2 = Finding(id=uuid.uuid4(), analysis_run_id=run_id, rule_id="GAP-01", rule_version="1.0.0", cse_id=cse_id, severity=FindingSeverity.CRITICAL, confidence=1.0, reason="Dup 2", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW)
        f3 = Finding(id=uuid.uuid4(), analysis_run_id=run_id, rule_id="GAP-01", rule_version="1.0.0", cse_id=cse_id, severity=FindingSeverity.HIGH, confidence=1.0, reason="Dup 3", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW)

        db.add_all([f1, f2, f3])
        db.commit()

        rs = SupervisoryRiskEngine.compute_cse_risk_score(db, cse_id, run_id)
        # Deduplication takes max (30.0) for execution_gap category, not 18+30+25 = 73
        assert rs.component_breakdown["execution_gap"] == 30.0

    finally:
        db.close()


def test_scenario_f_suppressed_finding_zero_risk():
    """Scenario F: Suppressed findings yield 0 risk contribution."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        cse_id = uuid.uuid4()
        run_id = uuid.uuid4()

        cse = CSE(id=cse_id, name="Maint CSE", sector="ENERGY", entity_type="UTILITY", size_tier="TIER_1")
        run = AnalysisRun(id=run_id, dataset_import_id=uuid.uuid4(), rule_version="1.0.0", model_version="1.0.0")
        db.add_all([cse, run])
        db.commit()

        f_suppressed = Finding(
            id=uuid.uuid4(), analysis_run_id=run_id, rule_id="NEG-05", rule_version="1.0.0",
            cse_id=cse_id, severity=FindingSeverity.HIGH, confidence=1.0, reason="SUPPRESSED due to maintenance",
            expected_behaviour="E", observed_behaviour="SUPPRESSED", evidence_refs=[], recommendation="R", status=FindingStatus.SUPPRESSED
        )
        db.add(f_suppressed)
        db.commit()

        rs = SupervisoryRiskEngine.compute_cse_risk_score(db, cse_id, run_id)
        assert rs.component_breakdown["negative_space"] == 0.0
        assert rs.normalized_score == 0.0
        assert rs.risk_band == "LOW"

    finally:
        db.close()


def test_scenario_g_low_confidence_qualification():
    """Scenario G: Low confidence (<0.70) explicitly qualifies and scales risk contribution."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        cse_id = uuid.uuid4()
        run_id = uuid.uuid4()

        cse = CSE(id=cse_id, name="LowConf CSE", sector="BANKING", entity_type="BANK", size_tier="TIER_1")
        run = AnalysisRun(id=run_id, dataset_import_id=uuid.uuid4(), rule_version="1.0.0", model_version="1.0.0")
        db.add_all([cse, run])
        db.commit()

        # Confidence = 0.60
        f_low_conf = Finding(
            id=uuid.uuid4(), analysis_run_id=run_id, rule_id="GAP-01", rule_version="1.0.0",
            cse_id=cse_id, severity=FindingSeverity.CRITICAL, confidence=0.60, reason="Incomplete logs",
            expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW
        )
        db.add(f_low_conf)
        db.commit()

        rs = SupervisoryRiskEngine.compute_cse_risk_score(db, cse_id, run_id)
        # Base 30.0 * max(0.50, 0.60) = 30.0 * 0.60 = 18.0
        assert rs.component_breakdown["execution_gap"] == 18.0
        assert rs.overall_confidence == 0.60
        assert len(rs.explanation_json["confidence_qualifications"]) == 1

    finally:
        db.close()


def test_scenario_i_multiple_cses_isolation():
    """Scenario I: Multiple CSEs processed simultaneously have strict isolation (no cross-contamination)."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        run_id = uuid.uuid4()
        cse1_id = uuid.uuid4()
        cse2_id = uuid.uuid4()

        cse1 = CSE(id=cse1_id, name="CSE Alpha", sector="ENERGY", entity_type="UTILITY", size_tier="TIER_1")
        cse2 = CSE(id=cse2_id, name="CSE Beta", sector="TELECOM", entity_type="TELCO", size_tier="TIER_1")
        run = AnalysisRun(id=run_id, dataset_import_id=uuid.uuid4(), rule_version="1.0.0", model_version="1.0.0")
        db.add_all([cse1, cse2, run])
        db.commit()

        # Finding ONLY for cse1
        f1 = Finding(id=uuid.uuid4(), analysis_run_id=run_id, rule_id="GAP-01", rule_version="1.0.0", cse_id=cse1_id, severity=FindingSeverity.CRITICAL, confidence=1.0, reason="G", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW)
        db.add(f1)
        db.commit()

        scores = SupervisoryRiskEngine.run_analysis(db, run_id)
        assert len(scores) == 2

        rs1 = next(s for s in scores if s.cse_id == cse1_id)
        rs2 = next(s for s in scores if s.cse_id == cse2_id)

        assert rs1.normalized_score == 30.0
        assert rs2.normalized_score == 0.0  # Zero risk for CSE Beta

    finally:
        db.close()


def test_scenario_j_k_l_reproducibility_idempotency_provenance():
    """Scenario J/K/L: Test reproducibility, idempotency (in-place update), and provenance."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        cse_id = uuid.uuid4()
        run_id = uuid.uuid4()

        cse = CSE(id=cse_id, name="Repro CSE", sector="ENERGY", entity_type="UTILITY", size_tier="TIER_1")
        run = AnalysisRun(id=run_id, dataset_import_id=uuid.uuid4(), rule_version="1.2.0", model_version="2.0.0")
        db.add_all([cse, run])
        db.commit()

        f = Finding(id=uuid.uuid4(), analysis_run_id=run_id, rule_id="NEG-01", rule_version="1.2.0", cse_id=cse_id, severity=FindingSeverity.HIGH, confidence=1.0, reason="Silence", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW)
        db.add(f)
        db.commit()

        # First Execution
        rs1 = SupervisoryRiskEngine.compute_cse_risk_score(db, cse_id, run_id)
        rs1_id = rs1.id
        score1 = rs1.normalized_score

        # Second Execution (Idempotent update)
        rs2 = SupervisoryRiskEngine.compute_cse_risk_score(db, cse_id, run_id)
        assert rs2.id == rs1_id  # Same database record ID (no duplicates created!)
        assert rs2.normalized_score == score1  # Identical score
        assert rs2.rule_version == "1.2.0"
        assert rs2.provenance_json["engine"] == "SupervisoryRiskEngine"

        # Verify DB contains exactly 1 RiskScore row
        count = db.query(RiskScore).filter(RiskScore.cse_id == cse_id).count()
        assert count == 1

    finally:
        db.close()


def test_scenario_n_risk_band_boundaries():
    """Scenario N: Boundary testing for risk bands (0, 24.99, 25, 49.99, 50, 74.99, 75, 100)."""
    assert SupervisoryRiskEngine.classify_risk_band(0.0) == "LOW"
    assert SupervisoryRiskEngine.classify_risk_band(24.99) == "LOW"
    assert SupervisoryRiskEngine.classify_risk_band(25.0) == "MODERATE"
    assert SupervisoryRiskEngine.classify_risk_band(49.99) == "MODERATE"
    assert SupervisoryRiskEngine.classify_risk_band(50.0) == "HIGH"
    assert SupervisoryRiskEngine.classify_risk_band(74.99) == "HIGH"
    assert SupervisoryRiskEngine.classify_risk_band(75.0) == "CRITICAL"
    assert SupervisoryRiskEngine.classify_risk_band(100.0) == "CRITICAL"


def test_risk_api_endpoints():
    """Test API endpoints: GET /api/v1/risk/cse/{cse_id} and GET /api/v1/risk/run/{analysis_run_id}."""
    client = TestClient(fastapi_app)
    db: Session = SessionLocal()
    try:
        clear_db(db)
        cse_id = uuid.uuid4()
        run_id = uuid.uuid4()

        cse = CSE(id=cse_id, name="API Risk CSE", sector="BANKING", entity_type="BANK", size_tier="TIER_1")
        run = AnalysisRun(id=run_id, dataset_import_id=uuid.uuid4(), rule_version="1.0.0", model_version="1.0.0")
        db.add_all([cse, run])
        db.commit()

        f = Finding(id=uuid.uuid4(), analysis_run_id=run_id, rule_id="GAP-01", rule_version="1.0.0", cse_id=cse_id, severity=FindingSeverity.HIGH, confidence=1.0, reason="G", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW)
        db.add(f)
        db.commit()

        SupervisoryRiskEngine.compute_cse_risk_score(db, cse_id, run_id)

        # GET /api/v1/risk/cse/{cse_id}
        r1 = client.get(f"/api/v1/risk/cse/{cse_id}")
        assert r1.status_code == 200
        d1 = r1.json()
        assert d1["cse_id"] == str(cse_id)
        assert d1["normalized_score"] == 25.0
        assert d1["risk_band"] == "MODERATE"
        assert "explanation" in d1

        # GET /api/v1/risk/run/{analysis_run_id}
        r2 = client.get(f"/api/v1/risk/run/{run_id}")
        assert r2.status_code == 200
        d2 = r2.json()
        assert len(d2) == 1
        assert d2[0]["analysis_run_id"] == str(run_id)

        # GET /api/v1/risk/scores/latest
        r3 = client.get("/api/v1/risk/scores/latest")
        assert r3.status_code == 200
        d3 = r3.json()
        assert len(d3) >= 1
        assert d3[0]["analysis_run_id"] == str(run_id)

    finally:
        db.close()



def test_risk_engine_benchmark():
    """Benchmark SupervisoryRiskEngine throughput across multiple CSEs."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        run_id = uuid.uuid4()
        run = AnalysisRun(id=run_id, dataset_import_id=uuid.uuid4(), rule_version="1.0.0", model_version="1.0.0")
        db.add(run)

        cses = []
        findings = []
        for i in range(50):
            c_id = uuid.uuid4()
            c = CSE(id=c_id, name=f"CSE Bench {i}", sector="ENERGY", entity_type="UTILITY", size_tier="TIER_1")
            cses.append(c)
            f = Finding(id=uuid.uuid4(), analysis_run_id=run_id, rule_id="GAP-01", rule_version="1.0.0", cse_id=c_id, severity=FindingSeverity.HIGH, confidence=1.0, reason="B", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW)
            findings.append(f)

        db.add_all(cses + findings)
        db.commit()

        start_time = time.time()
        scores = SupervisoryRiskEngine.run_analysis(db, run_id)
        duration = time.time() - start_time
        throughput = len(cses) / duration if duration > 0 else 0.0

        assert len(scores) == 50
        assert duration >= 0.0
        assert throughput > 1.0  # Stable execution throughput (>1 CSE/sec under full test suite load)

    finally:
        db.close()
