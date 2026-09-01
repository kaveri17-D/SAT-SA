import uuid
import pytest
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.core.database import SessionLocal
from app.models import AnalysisRun, DatasetImport, Finding, Evidence, RiskScore, ReviewQueueItem, AuditLog, MaintenanceLog
from app.ingestion.generator.engine import SyntheticDatasetGenerator, GeneratorConfig

from app.rules.service import ExecutionGapEngine, NegativeSpaceEngine

from app.analytics.risk_engine import SupervisoryRiskEngine
from app.analytics.prioritization_engine import ReviewPrioritizationEngine
from app.analytics.graph_engine import SupervisoryEvidenceGraphEngine
from app.evidence.assembler import EvidenceAssembler
from app.main import app as fastapi_app


def clear_db(db: Session):
    db.query(AuditLog).delete()
    db.query(ReviewQueueItem).delete()
    db.query(RiskScore).delete()
    db.query(Finding).delete()
    db.query(Evidence).delete()
    db.query(AnalysisRun).delete()
    db.query(DatasetImport).delete()
    db.commit()


def test_full_end_to_end_pipeline_validation():
    """Prove that a fresh dataset travels through the complete SAT-SA architecture maintaining 100% provenance."""
    db: Session = SessionLocal()
    client = TestClient(fastapi_app)
    try:
        clear_db(db)
        
        # 1. Dataset Generation
        config = GeneratorConfig(num_cses=5, total_alerts=500, seed=123)

        dataset = SyntheticDatasetGenerator(config).generate()

        assert len(dataset["alerts"]) >= 500
        alert_count = len(dataset["alerts"])

        # 2. DatasetImport Provenance Record
        import_id = uuid.uuid4()
        run_id = uuid.uuid4()

        ds_import = DatasetImport(
            id=import_id,
            filename="e2e_validation_test.csv",
            source="SYNTHETIC_DATASET_GENERATOR",
            imported_at=datetime.now(timezone.utc),
            imported_by="E2E_TEST_SUITE",
            row_count=alert_count,
            accepted_count=alert_count,
            quarantined_count=0,
            status="COMPLETED",
            completeness_score=100.0
        )

        run = AnalysisRun(
            id=run_id,
            dataset_import_id=import_id,
            rule_version="1.0.0",
            model_version="1.0.0",
            status="RUNNING"
        )

        db.add_all([ds_import, run])
        # Add generated dataset entities to database
        for key in ["cses", "assets", "analysts", "alerts", "investigations", "escalations", "cases", "closures", "maintenance_logs"]:
            for item in dataset[key]:
                if isinstance(item, dict):
                    if key == "maintenance_logs":
                        item = MaintenanceLog(
                            id=uuid.UUID(item["id"]) if isinstance(item["id"], str) else item["id"],
                            asset_id=uuid.UUID(item["asset_id"]) if isinstance(item["asset_id"], str) else item["asset_id"],
                            cse_id=uuid.UUID(item["cse_id"]) if isinstance(item["cse_id"], str) else item["cse_id"],
                            maintenance_ref=item["maintenance_ref"],
                            start_time=datetime.fromisoformat(item["start_time"]) if isinstance(item["start_time"], str) else item["start_time"],
                            end_time=datetime.fromisoformat(item["end_time"]) if isinstance(item["end_time"], str) else item["end_time"],
                            reason=item.get("reason", ""),
                            approved_by=item.get("approved_by", "")
                        )
                db.add(item)
        db.commit()


        # 3. Execution Gap & Negative Space Detection Engines
        gap_engine = ExecutionGapEngine(db=db)
        gap_engine.run_analysis(dataset_import_id=import_id, analysis_run_id=run_id)

        neg_engine = NegativeSpaceEngine(db=db)
        neg_engine.run_analysis(dataset_import_id=import_id, analysis_run_id=run_id)


        all_findings = db.query(Finding).filter(Finding.analysis_run_id == run_id).all()
        assert len(all_findings) > 0

        # Provenance check on findings
        for f in all_findings:
            assert f.analysis_run_id == run_id

        # 4. Supervisory Risk Engine
        risk_scores = SupervisoryRiskEngine.compute_supervisory_risk(db, run_id)
        assert len(risk_scores) > 0
        for r in risk_scores:
            assert r.analysis_run_id == run_id

        # 5. Review Prioritization Engine
        queue, p_metrics = ReviewPrioritizationEngine.generate_review_queue(db, run_id, target_queue_size=10)
        assert len(queue) == 10
        for q in queue:
            assert q.analysis_run_id == run_id

        # 6. Evidence Engine & Cryptographic SHA-256 Verification
        top_finding_id = queue[0].finding_id
        verify_res = EvidenceAssembler.verify_evidence_integrity(db, top_finding_id)
        assert verify_res["status"] == "VERIFIED"
        assert verify_res["is_tampered"] is False
        assert len(verify_res["sha256_hash"]) == 64

        # 7. Supervisory Evidence Graph Engine
        G = SupervisoryEvidenceGraphEngine.build_graph_for_analysis_run(db, run_id)
        assert G.number_of_nodes() > 0
        assert G.number_of_edges() > 0

        # 8. FastAPI Endpoint & Examiner Workflow Verification
        queue_item_id = str(queue[0].id)
        r_status = client.post(
            f"/api/v1/prioritization/item/{queue_item_id}/status",
            json={"status": "IN_REVIEW", "notes": "E2E pipeline test review", "user_id": "EXAMINER_E2E"}
        )
        assert r_status.status_code == 200
        assert r_status.json()["status"] == "IN_REVIEW"

        # 9. AuditLog Persistence
        audit_entry = db.query(AuditLog).filter(AuditLog.entity_id == queue_item_id).first()
        assert audit_entry is not None
        assert audit_entry.before_after_json.get("new_status") == "IN_REVIEW"
        assert audit_entry.user_id == "EXAMINER_E2E"


        # 10. Update AnalysisRun to COMPLETED
        run.status = "COMPLETED"
        db.commit()

        # 11. Verify API metrics endpoint returns E2E active run metrics
        r_metrics = client.get("/api/v1/prioritization/metrics/latest")
        assert r_metrics.status_code == 200
        m = r_metrics.json()
        assert m["analysis_run_id"] == str(run_id)
        assert m["total_findings"] == len(all_findings)

    finally:
        db.close()
