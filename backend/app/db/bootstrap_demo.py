import os
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine
from app.models import (
    Base, CSE, Asset, Analyst, Alert, Investigation, Escalation, Case, Closure, MaintenanceLog,
    DatasetImport, DatasetImportStatus, DataQualityIssue, AnalysisRun, Finding, Evidence, RiskScore, ReviewQueueItem, AuditLog
)
from app.db.seed import seed_baseline_reference_data
from app.ingestion.generator.engine import SyntheticDatasetGenerator
from app.ingestion.generator.config import GeneratorConfig
from app.rules.service import ExecutionGapEngine, NegativeSpaceEngine
from app.evidence.assembler import EvidenceAssembler
from app.analytics.risk_engine import SupervisoryRiskEngine
from app.analytics.prioritization_engine import ReviewPrioritizationEngine
from app.analytics.graph_engine import SupervisoryEvidenceGraphEngine
from app.core.logging import logger


def bootstrap_demo_dataset(db: Session = None, force_rebuild: bool = False) -> uuid.UUID:
    """Idempotently bootstrap real database-backed synthetic data, runs analytics, risk engine, review queue, and evidence graph."""
    close_session = False
    if db is None:
        db = SessionLocal()
        close_session = True

    try:
        if force_rebuild:
            logger.info("Dropping stale database tables and recreating schema...")
            Base.metadata.drop_all(bind=engine)
            Base.metadata.create_all(bind=engine)
        else:
            logger.info("Ensuring database schema tables exist...")
            Base.metadata.create_all(bind=engine)

        # Seed baseline reference rules and model versions
        seed_baseline_reference_data(db)

        # Idempotency check
        existing_run = db.query(AnalysisRun).filter(AnalysisRun.status == "COMPLETED").order_by(AnalysisRun.created_at.desc()).first()
        existing_cses = db.query(CSE).count()
        existing_queue = db.query(ReviewQueueItem).count()

        if not force_rebuild and existing_cses > 0 and existing_run and existing_queue > 0:
            logger.info(f"Demo database already initialized with {existing_cses} CSEs, Run '{existing_run.id}', and {existing_queue} Review Queue Items.")
            return existing_run.id

        logger.info("Generating deterministic synthetic dataset (seed=42)...")
        gen = SyntheticDatasetGenerator(config=GeneratorConfig.baseline_preset())
        data = gen.generate()

        logger.info("Ingesting synthetic dataset into canonical database...")
        # Add CSEs
        for c in data["cses"]:
            if not db.query(CSE).filter(CSE.id == c.id).first():
                db.add(c)
        db.commit()

        # Add Assets
        for a in data["assets"]:
            if not db.query(Asset).filter(Asset.id == a.id).first():
                db.add(a)
        db.commit()

        # Add Analysts
        for an in data["analysts"]:
            if not db.query(Analyst).filter(Analyst.id == an.id).first():
                db.add(an)
        db.commit()

        # Add Alerts
        for alt in data["alerts"]:
            if not db.query(Alert).filter(Alert.id == alt.id).first():
                db.add(alt)
        db.commit()

        # Add Investigations
        for inv in data["investigations"]:
            if not db.query(Investigation).filter(Investigation.id == inv.id).first():
                db.add(inv)
        db.commit()

        # Add Escalations
        for esc in data["escalations"]:
            if not db.query(Escalation).filter(Escalation.id == esc.id).first():
                db.add(esc)
        db.commit()

        # Add Cases
        for cs in data["cases"]:
            if not db.query(Case).filter(Case.id == cs.id).first():
                db.add(cs)
        db.commit()

        # Add Closures
        for cl in data["closures"]:
            if not db.query(Closure).filter(Closure.id == cl.id).first():
                db.add(cl)
        db.commit()

        # Add Maintenance Logs
        if "maintenance_logs" in data:
            for m in data["maintenance_logs"]:
                if isinstance(m, dict):
                    m_id = uuid.UUID(m["id"]) if isinstance(m["id"], str) else m["id"]
                    if not db.query(MaintenanceLog).filter(MaintenanceLog.id == m_id).first():
                        start_dt = datetime.fromisoformat(m["start_time"]) if isinstance(m["start_time"], str) else m["start_time"]
                        end_dt = datetime.fromisoformat(m["end_time"]) if isinstance(m["end_time"], str) else m["end_time"]
                        m_obj = MaintenanceLog(
                            id=m_id,
                            cse_id=uuid.UUID(m["cse_id"]) if isinstance(m["cse_id"], str) else m["cse_id"],
                            asset_id=uuid.UUID(m["asset_id"]) if m.get("asset_id") and isinstance(m["asset_id"], str) else m.get("asset_id"),
                            maintenance_ref=m["maintenance_ref"],
                            start_time=start_dt,
                            end_time=end_dt,
                            reason=m.get("reason"),
                            approved_by=m.get("approved_by")
                        )
                        db.add(m_obj)
                else:
                    if not db.query(MaintenanceLog).filter(MaintenanceLog.id == m.id).first():
                        db.add(m)
            db.commit()

        # Record DatasetImport Provenance
        ds_import = DatasetImport(
            id=uuid.uuid4(),
            filename="synthetic_baseline.csv",
            source="SYNTHETIC_DATASET_GENERATOR",
            imported_at=datetime.now(timezone.utc),
            imported_by="DEMO_BOOTSTRAP",
            row_count=len(data["alerts"]),
            accepted_count=len(data["alerts"]),
            quarantined_count=0,
            status=DatasetImportStatus.COMPLETED,
            completeness_score=100.0
        )
        db.add(ds_import)
        db.commit()

        # 4. Run Analytics Engines (Execution Gap & Negative Space)
        logger.info(f"Executing ExecutionGapEngine for DatasetImport '{ds_import.id}'...")
        gap_engine = ExecutionGapEngine(db)
        analysis_run = gap_engine.run_analysis(ds_import.id)
        analysis_run_id = analysis_run.id

        logger.info(f"Executing NegativeSpaceEngine for DatasetImport '{ds_import.id}'...")
        neg_engine = NegativeSpaceEngine(db)
        neg_run = neg_engine.run_analysis(ds_import.id, analysis_run_id=analysis_run_id)

        # 5. Count Assembled Evidence Records
        ev_count = db.query(Evidence).count()
        logger.info(f"Verified {ev_count} assembled Evidence records across findings.")

        # 6. Calculate Supervisory Risk Scores
        logger.info("Calculating CSE Supervisory Risk Scores...")
        risk_scores = SupervisoryRiskEngine.run_analysis(db, analysis_run_id)
        logger.info(f"Computed Supervisory Risk Scores for {len(risk_scores)} CSEs.")

        # 7. Generate Review Prioritization Queue
        logger.info("Generating Ranked Review Prioritization Queue...")
        queue_items, metrics = ReviewPrioritizationEngine.generate_review_queue(db, analysis_run_id)
        logger.info(f"Generated {len(queue_items)} ranked Review Queue Items.")

        # 8. Verify Supervisory Evidence Graph Engine
        logger.info("Verifying Supervisory Evidence Graph Engine...")
        G = SupervisoryEvidenceGraphEngine.build_graph_for_analysis_run(db, analysis_run_id)
        anomalies = SupervisoryEvidenceGraphEngine.detect_graph_anomalies(db, G, analysis_run_id)
        logger.info(f"Supervisory Evidence Graph initialized: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges, {len(anomalies)} graph anomalies detected.")

        logger.info("=== DEMO DATA BOOTSTRAP COMPLETE ===")
        logger.info(f"Active AnalysisRun ID: {analysis_run_id}")
        return analysis_run_id

    finally:
        if close_session:
            db.close()


if __name__ == "__main__":
    bootstrap_demo_dataset(force_rebuild=True)
