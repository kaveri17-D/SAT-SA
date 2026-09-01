"""Phase 19: Clean Reinstall & Isolated Cold-Start Deployment Test."""
import os
import sys
import uuid
import tempfile
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.db.seed import seed_baseline_reference_data
from app.models import CSE, Asset, Alert, Finding, AnalysisRun, DatasetImport, AssetCriticality, AlertSeverity, FindingSeverity, FindingStatus
from app.analytics.risk_engine import SupervisoryRiskEngine
from app.analytics.prioritization_engine import ReviewPrioritizationEngine
from app.analytics.graph_engine import SupervisoryEvidenceGraphEngine
from app.reporting.builder import ReportBuilder
from app.reporting.schemas import ReportGenerateRequest, ReportType
from app.audit.service import AuditService


def test_clean_isolated_deployment():
    print("=================================================================")
    print("SAT-SA PHASE 19 — CLEAN REINSTALL & ISOLATED COLD-START TEST")
    print("=================================================================")

    temp_dir = tempfile.mkdtemp(prefix="satsa_clean_deploy_")
    db_path = os.path.join(temp_dir, "isolated_satsa.db")
    db_url = f"sqlite:///{db_path}"
    print(f"[*] Target Isolated Database: {db_path}")

    test_engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    # 1. Zero-Touch Database Bootstrap
    print("[*] Executing zero-touch schema creation & baseline rule seeding...")
    Base.metadata.create_all(bind=test_engine)
    db = TestSessionLocal()
    try:
        seed_baseline_reference_data(db)
        print("[+] Baseline reference data successfully seeded on clean database.")

        # 2. Ingest Sample Multi-CSE Telemetry
        cse = CSE(name="ISOLATED_CLEAN_TEST_GRID", sector="ENERGY", entity_type="GRID", size_tier="TIER_1")
        db.add(cse)
        db.flush()

        asset = Asset(cse_id=cse.id, name="CLEAN_TEST_RTU", asset_type="RTU", criticality=AssetCriticality.CRITICAL)
        db.add(asset)
        db.flush()

        alert = Alert(cse_id=cse.id, asset_id=asset.id, source_system="SIEM", category="FIRMWARE", severity=AlertSeverity.CRITICAL, raw_severity="CRITICAL", status="OPEN")
        db.add(alert)
        db.flush()

        ds = DatasetImport(filename="clean_deploy_sample.json", source="SIEM", imported_by="ISOLATED_EXAMINER", row_count=1)
        db.add(ds)
        db.flush()

        run_id = uuid.uuid4()
        run = AnalysisRun(id=run_id, dataset_import_id=ds.id, status="COMPLETED", rule_version="1.0.0", model_version="1.0.0")
        db.add(run)
        db.flush()

        finding = Finding(
            analysis_run_id=run_id,
            cse_id=cse.id,
            asset_id=asset.id,
            rule_id="GAP-01",
            rule_version="1.0.0",
            severity=FindingSeverity.CRITICAL,
            anomaly_score=0.95,
            confidence=0.99,
            supervisory_priority=9.5,
            evidence_completeness=1.0,
            reason="Isolated cold-start gap detection.",
            expected_behaviour="Triage within 60 min.",
            observed_behaviour="Untriaged.",
            recommendation="Isolate RTU subnet and verify cryptographic firmware signatures.",
            status=FindingStatus.NEW,
            evidence_refs=[{"source": "alerts", "id": str(alert.id)}]
        )
        db.add(finding)
        db.commit()
        print("[+] Sample telemetry and finding recorded.")

        # 3. Analytics Execution
        print("[*] Running analytical engines on isolated instance...")
        risk_scores = SupervisoryRiskEngine.run_analysis(db, run_id)
        assert len(risk_scores) >= 1
        queue_items, q_meta = ReviewPrioritizationEngine.generate_review_queue(db, run_id)
        assert len(queue_items) >= 1
        G = SupervisoryEvidenceGraphEngine.build_graph_for_analysis_run(db, run_id)
        assert G.number_of_nodes() >= 3

        # 4. Report Generation & Audit Ledger Verification
        req = ReportGenerateRequest(
            assessment_id=str(run_id),
            report_type=ReportType.EXECUTIVE,
            cse_id=str(cse.id),
            title="Clean Deployment Executive Snapshot",
            generated_by="ISOLATED_EXAMINER"
        )
        snap = ReportBuilder.generate_report(db, req)
        assert snap.sha256_checksum is not None
        print(f"[+] Report Snapshot Generated: Number={snap.report_number}, SHA-256={snap.sha256_checksum}")

        is_valid, total, verified, failed_id, msg = AuditService.verify_audit_trail_integrity(db)
        assert is_valid is True
        print(f"[+] Audit Trail Verified: {verified}/{total} events cryptographically valid.")

    finally:
        db.close()
        test_engine.dispose()

    # Clean up isolated temp directory
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(temp_dir)
    except Exception:
        pass

    print("=================================================================")
    print("[OK] CLEAN COLD-START REINSTALL TEST PASSED WITH ZERO BLOCKERS!")
    print("=================================================================")
    return True


if __name__ == "__main__":
    test_clean_isolated_deployment()
