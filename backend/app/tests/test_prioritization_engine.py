import uuid
import time
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.core.database import SessionLocal, Base, engine
from app.models import (
    CSE, Asset, Finding, AnalysisRun, RiskScore, ReviewQueueItem, AuditLog,
    FindingSeverity, FindingStatus, QueueItemStatus, AssetCriticality
)
from app.analytics.prioritization_engine import ReviewPrioritizationEngine, FACTOR_WEIGHTS
from app.main import app as fastapi_app


def clear_db(db: Session):
    db.query(AuditLog).delete()
    db.query(ReviewQueueItem).delete()
    db.query(RiskScore).delete()
    db.query(Finding).delete()
    db.query(AnalysisRun).delete()
    db.query(Asset).delete()
    db.query(CSE).delete()
    db.commit()
    db.expire_all()


def test_prioritization_8_factor_calculation():
    """Test decomposable 8-factor formula calculation."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        cse_id = uuid.uuid4()
        run_id = uuid.uuid4()

        cse = CSE(id=cse_id, name="Test CSE", sector="ENERGY", entity_type="UTILITY", size_tier="TIER_1")
        asset = Asset(id=uuid.uuid4(), cse_id=cse_id, name="Core-Router", asset_type="NET", criticality=AssetCriticality.CRITICAL, status="ACTIVE")
        run = AnalysisRun(id=run_id, dataset_import_id=uuid.uuid4(), rule_version="1.0.0", model_version="1.0.0")
        db.add_all([cse, asset, run])
        db.commit()

        f = Finding(
            id=uuid.uuid4(), analysis_run_id=run_id, rule_id="GAP-01", rule_version="1.0.0",
            cse_id=cse_id, asset_id=asset.id, severity=FindingSeverity.CRITICAL, confidence=1.0,
            evidence_completeness=100.0, anomaly_score=0.9, risk_score=85.0, supervisory_priority=85.0,
            reason="Gap", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW
        )
        db.add(f)
        db.commit()

        p_score, factors, qual = ReviewPrioritizationEngine.compute_candidate_score(f, 85.0, asset)
        assert factors["risk_significance"] == 85.0
        assert factors["finding_severity"] == 100.0
        assert factors["asset_criticality"] == 100.0
        assert factors["evidence_completeness"] == 100.0
        assert factors["evidence_confidence"] == 100.0
        assert factors["novelty"] == 100.0
        assert factors["review_urgency"] == 90.0

        # Independent formula verification:
        expected_score = round(
            85.0 * 0.25 + 100.0 * 0.20 + 100.0 * 0.15 + 100.0 * 0.15 + 100.0 * 0.10 + 100.0 * 0.05 + 0.0 * 0.05 + 90.0 * 0.05, 2
        )
        assert p_score == expected_score == 90.75

    finally:
        db.close()


def test_suppressed_and_dismissed_exclusion():
    """Test that SUPPRESSED and DISMISSED findings do NOT enter the active review queue."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        cse_id = uuid.uuid4()
        run_id = uuid.uuid4()

        cse = CSE(id=cse_id, name="Maint CSE", sector="ENERGY", entity_type="UTILITY", size_tier="TIER_1")
        run = AnalysisRun(id=run_id, dataset_import_id=uuid.uuid4(), rule_version="1.0.0", model_version="1.0.0")
        db.add_all([cse, run])
        db.commit()

        f_new = Finding(id=uuid.uuid4(), analysis_run_id=run_id, rule_id="GAP-01", cse_id=cse_id, severity=FindingSeverity.HIGH, confidence=1.0, reason="G1", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW)
        f_suppressed = Finding(id=uuid.uuid4(), analysis_run_id=run_id, rule_id="NEG-01", cse_id=cse_id, severity=FindingSeverity.HIGH, confidence=1.0, reason="G2", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.SUPPRESSED)
        f_dismissed = Finding(id=uuid.uuid4(), analysis_run_id=run_id, rule_id="NEG-02", cse_id=cse_id, severity=FindingSeverity.HIGH, confidence=1.0, reason="G3", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.DISMISSED)

        db.add_all([f_new, f_suppressed, f_dismissed])
        db.commit()

        queue, metrics = ReviewPrioritizationEngine.generate_review_queue(db, run_id)
        assert len(queue) == 1
        assert queue[0].finding_id == f_new.id

    finally:
        db.close()


def test_low_evidence_completeness_uncertainty_penalty():
    """Test that low evidence completeness (<40%) incurs explicit -15 penalty."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        cse_id = uuid.uuid4()
        run_id = uuid.uuid4()

        cse = CSE(id=cse_id, name="LowComp CSE", sector="BANKING", entity_type="BANK", size_tier="TIER_1")
        run = AnalysisRun(id=run_id, dataset_import_id=uuid.uuid4(), rule_version="1.0.0", model_version="1.0.0")
        db.add_all([cse, run])
        db.commit()

        f_low = Finding(
            id=uuid.uuid4(), analysis_run_id=run_id, rule_id="GAP-01", cse_id=cse_id,
            severity=FindingSeverity.CRITICAL, confidence=1.0, evidence_completeness=20.0,
            reason="Incomplete data", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW
        )
        db.add(f_low)
        db.commit()

        p_score, factors, qual = ReviewPrioritizationEngine.compute_candidate_score(f_low, 50.0, None)
        assert len(qual) == 1
        assert "penalized by -15.0" in qual[0]

    finally:
        db.close()


def test_two_pass_diversity_and_adversarial_concentration():
    """Adversarial test: CSE-A has 8 independent findings. Diversity limits pass 1, pass 2 fallback preserves systemic concentration."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        run_id = uuid.uuid4()
        cse_a_id = uuid.uuid4()
        cse_b_id = uuid.uuid4()

        cse_a = CSE(id=cse_a_id, name="Concentrated CSE-A", sector="ENERGY", entity_type="POWER", size_tier="TIER_1")
        cse_b = CSE(id=cse_b_id, name="Normal CSE-B", sector="TELECOM", entity_type="TELCO", size_tier="TIER_1")
        run = AnalysisRun(id=run_id, dataset_import_id=uuid.uuid4(), rule_version="1.0.0", model_version="1.0.0")
        db.add_all([cse_a, cse_b, run])
        db.commit()

        # 8 critical findings for CSE-A across different rule IDs
        findings_a = [
            Finding(id=uuid.uuid4(), analysis_run_id=run_id, rule_id=f"GAP-0{i%5+1}", cse_id=cse_a_id, severity=FindingSeverity.CRITICAL, confidence=1.0, reason=f"Crit A-{i}", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW)
            for i in range(8)
        ]
        # 1 finding for CSE-B
        f_b = Finding(id=uuid.uuid4(), analysis_run_id=run_id, rule_id="NEG-01", cse_id=cse_b_id, severity=FindingSeverity.HIGH, confidence=1.0, reason="High B", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW)

        db.add_all(findings_a + [f_b])
        db.commit()

        # Generate queue with max_per_cse=2, target_queue_size=5
        queue, metrics = ReviewPrioritizationEngine.generate_review_queue(db, run_id, max_per_cse=2, max_per_category=3, target_queue_size=5)

        # Pass 1 takes 2 from CSE-A and 1 from CSE-B = 3 items. Pass 2 fills remaining 2 items from CSE-A candidates!
        assert len(queue) == 5
        assert metrics["candidates_reintroduced_by_fallback"] > 0
        assert metrics["systemic_concentration_detected"] is True

    finally:
        db.close()


def test_deterministic_tie_breaking_and_reproducibility():
    """Test deterministic tie-breaking and exact reproducibility across runs."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        cse_id = uuid.uuid4()
        run_id = uuid.uuid4()

        cse = CSE(id=cse_id, name="Tie CSE", sector="BANKING", entity_type="BANK", size_tier="TIER_1")
        run = AnalysisRun(id=run_id, dataset_import_id=uuid.uuid4(), rule_version="1.0.0", model_version="1.0.0")
        db.add_all([cse, run])
        db.commit()

        f1 = Finding(id=uuid.uuid4(), analysis_run_id=run_id, rule_id="GAP-01", cse_id=cse_id, severity=FindingSeverity.HIGH, confidence=1.0, reason="Identical 1", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW)
        f2 = Finding(id=uuid.uuid4(), analysis_run_id=run_id, rule_id="GAP-01", cse_id=cse_id, severity=FindingSeverity.HIGH, confidence=1.0, reason="Identical 2", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW)
        db.add_all([f1, f2])
        db.commit()

        queue1, _ = ReviewPrioritizationEngine.generate_review_queue(db, run_id)
        ranks1 = [item.finding_id for item in queue1]

        # Re-run (Idempotent)
        queue2, _ = ReviewPrioritizationEngine.generate_review_queue(db, run_id)
        ranks2 = [item.finding_id for item in queue2]

        assert ranks1 == ranks2  # Identical deterministic ordering!

    finally:
        db.close()


def test_status_transition_and_audit_logging():
    """Test QueueItemStatus transition and immutable AuditLog generation."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        cse_id = uuid.uuid4()
        run_id = uuid.uuid4()

        cse = CSE(id=cse_id, name="Audit CSE", sector="ENERGY", entity_type="POWER", size_tier="TIER_1")
        run = AnalysisRun(id=run_id, dataset_import_id=uuid.uuid4(), rule_version="1.0.0", model_version="1.0.0")
        db.add_all([cse, run])
        db.commit()

        f = Finding(id=uuid.uuid4(), analysis_run_id=run_id, rule_id="GAP-01", cse_id=cse_id, severity=FindingSeverity.CRITICAL, confidence=1.0, reason="G", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW)
        db.add(f)
        db.commit()

        queue, _ = ReviewPrioritizationEngine.generate_review_queue(db, run_id)
        item = queue[0]
        assert item.status == QueueItemStatus.NEW

        # Transition NEW -> IN_REVIEW
        updated_item, audit = ReviewPrioritizationEngine.update_item_status(db, item.id, QueueItemStatus.IN_REVIEW, user_id="EXAMINER_01", notes="Started examination")
        assert updated_item.status == QueueItemStatus.IN_REVIEW
        assert audit.action == "UPDATE_QUEUE_ITEM_STATUS"
        assert audit.before_after_json["previous_status"] == "NEW"
        assert audit.before_after_json["new_status"] == "IN_REVIEW"

        # Transition IN_REVIEW -> RESOLVED
        updated_item2, audit2 = ReviewPrioritizationEngine.update_item_status(db, item.id, QueueItemStatus.RESOLVED, user_id="EXAMINER_01", notes="Validation complete")
        assert updated_item2.status == QueueItemStatus.RESOLVED
        assert audit2.before_after_json["previous_status"] == "IN_REVIEW"
        assert audit2.before_after_json["new_status"] == "RESOLVED"

    finally:
        db.close()


def test_prioritization_api_endpoints():
    """Test API endpoints: GET /api/v1/prioritization/queue/{analysis_run_id}, GET /item/{id}, POST /item/{id}/status."""
    client = TestClient(fastapi_app)
    db: Session = SessionLocal()
    try:
        clear_db(db)
        cse_id = uuid.uuid4()
        run_id = uuid.uuid4()

        cse = CSE(id=cse_id, name="API Prioritization CSE", sector="BANKING", entity_type="BANK", size_tier="TIER_1")
        run = AnalysisRun(id=run_id, dataset_import_id=uuid.uuid4(), rule_version="1.0.0", model_version="1.0.0")
        db.add_all([cse, run])
        db.commit()

        f = Finding(id=uuid.uuid4(), analysis_run_id=run_id, rule_id="GAP-01", cse_id=cse_id, severity=FindingSeverity.HIGH, confidence=1.0, reason="G", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW)
        db.add(f)
        db.commit()

        # 1. GET /api/v1/prioritization/queue/{analysis_run_id}
        r1 = client.get(f"/api/v1/prioritization/queue/{run_id}")
        assert r1.status_code == 200
        d1 = r1.json()
        assert d1["queue_count"] == 1
        item_id = d1["queue"][0]["queue_item_id"]

        # 2. GET /api/v1/prioritization/item/{queue_item_id}
        r2 = client.get(f"/api/v1/prioritization/item/{item_id}")
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["queue_item_id"] == item_id

        # 3. POST /api/v1/prioritization/item/{queue_item_id}/status
        r3 = client.post(f"/api/v1/prioritization/item/{item_id}/status", json={"status": "IN_REVIEW", "user_id": "EXAMINER_02", "notes": "Taking case"})
        assert r3.status_code == 200
        assert r3.json()["status"] == "IN_REVIEW"

    finally:
        db.close()


def test_prioritization_engine_benchmark():
    """Benchmark ReviewPrioritizationEngine throughput across candidates."""
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
            c = CSE(id=c_id, name=f"CSE Bench P9 {i}", sector="ENERGY", entity_type="UTILITY", size_tier="TIER_1")
            cses.append(c)
            f = Finding(id=uuid.uuid4(), analysis_run_id=run_id, rule_id=f"GAP-0{i%5+1}", cse_id=c_id, severity=FindingSeverity.HIGH, confidence=1.0, reason="B", expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW)
            findings.append(f)

        db.add_all(cses + findings)
        db.commit()

        start_time = time.time()
        queue, metrics = ReviewPrioritizationEngine.generate_review_queue(db, run_id, target_queue_size=20)
        duration = time.time() - start_time
        throughput = len(findings) / duration if duration > 0 else 0.0

        assert len(queue) == 20
        assert metrics["candidates_processed"] == 50
        assert throughput > 10.0  # High throughput (>10 candidates/sec)

    finally:
        db.close()


def test_dashboard_metrics_and_cses_regression():
    """Regression test: verify dashboard metrics and CSE endpoints return real non-zero records and analysis_run_id."""
    db: Session = SessionLocal()
    client = TestClient(fastapi_app)
    try:
        clear_db(db)
        run_id = uuid.uuid4()
        import_id = uuid.uuid4()
        cse_id = uuid.uuid4()

        run = AnalysisRun(id=run_id, dataset_import_id=import_id, rule_version="1.0.0", model_version="1.0.0", status="COMPLETED")
        cse = CSE(id=cse_id, name="Regression Energy Corp", sector="ENERGY", entity_type="UTILITY", size_tier="TIER_1")
        asset = Asset(id=uuid.uuid4(), cse_id=cse_id, name="Substation Alpha", asset_type="SUBSTATION", criticality=AssetCriticality.CRITICAL, status="ACTIVE")
        db.add_all([run, cse, asset])
        db.commit()

        finding = Finding(
            id=uuid.uuid4(), analysis_run_id=run_id, rule_id="GAP-01", cse_id=cse_id, asset_id=asset.id,
            severity=FindingSeverity.CRITICAL, confidence=1.0, evidence_completeness=95.0,
            anomaly_score=0.85, risk_score=80.0, supervisory_priority=80.0, reason="Regression gap",
            expected_behaviour="E", observed_behaviour="O", evidence_refs=[], recommendation="R", status=FindingStatus.NEW
        )
        risk_score = RiskScore(
            id=uuid.uuid4(), cse_id=cse_id, analysis_run_id=run_id, raw_score=65.0,
            normalized_score=65.0, risk_band="HIGH", overall_confidence=0.95,
            component_breakdown={"execution_gap": 30.0, "negative_space": 35.0}
        )


        db.add_all([finding, risk_score])
        db.commit()

        # Generate queue
        ReviewPrioritizationEngine.generate_review_queue(db, run_id)

        # 1. Test GET /api/v1/prioritization/metrics/latest
        r_metrics = client.get("/api/v1/prioritization/metrics/latest")
        assert r_metrics.status_code == 200
        m = r_metrics.json()
        assert m["total_cses"] == 1
        assert m["total_findings"] == 1
        assert m["critical_findings"] == 1
        assert m["high_priority_reviews"] == 1
        assert m["analysis_run_id"] == str(run_id)
        assert m["dataset_import_id"] == str(import_id)

        # 2. Test GET /api/v1/prioritization/cses
        r_cses = client.get("/api/v1/prioritization/cses")
        assert r_cses.status_code == 200
        cses_data = r_cses.json()
        assert len(cses_data) == 1
        assert cses_data[0]["cse_id"] == str(cse_id)
        assert cses_data[0]["finding_count"] == 1
        assert cses_data[0]["risk_score"] == 65.0
        assert cses_data[0]["risk_band"] == "HIGH"

    finally:
        db.close()

