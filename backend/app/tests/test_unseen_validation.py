import os
import tempfile
from datetime import datetime, timezone
import pytest
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, Base, engine
from app.models import (
    Finding, Evidence, AnalysisRun, CSE, Asset, Alert, MaintenanceLog, DatasetImport
)
from app.ingestion.pipeline import IngestionPipeline
from app.ingestion.generator.config import GeneratorConfig
from app.ingestion.generator.engine import SyntheticDatasetGenerator
from app.ingestion.generator.exporters import export_dataset_to_csv
from app.rules.service import NegativeSpaceEngine
from app.analytics.evaluator import GroundTruthEvaluator, EvaluationReport


from app.models import AuditLog, ReviewQueueItem, RiskScore

def clear_db(db: Session):
    db.query(AuditLog).delete()
    db.query(ReviewQueueItem).delete()
    db.query(RiskScore).delete()
    db.query(Evidence).delete()
    db.query(Finding).delete()
    db.query(AnalysisRun).delete()
    db.query(MaintenanceLog).delete()
    db.query(Alert).delete()
    db.query(Asset).delete()
    db.query(CSE).delete()
    db.query(DatasetImport).delete()
    db.commit()
    db.expire_all()


def test_unseen_dataset_evaluation_and_metrics():
    """Evaluate Negative Space Engine on an unseen synthetic dataset (seed=9999, 15 CSEs, 8500 alerts).

    Dataset contains:
    1. Clean normal entities
    2. Legitimate maintenance exceptions
    3. Decommissioned assets
    4. Non-applicable expected evidence categories
    5. Incomplete/low-quality data cases
    6. Injected negative-space scenarios (NEG-01..NEG-05)
    """
    config = GeneratorConfig(
        seed=9999,
        num_cses=15,
        total_alerts=8500,
        start_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
        duration_days=45
    )
    generator = SyntheticDatasetGenerator(config)
    dataset = generator.generate()

    with tempfile.TemporaryDirectory() as tmpdir:
        export_dataset_to_csv(dataset, tmpdir)

        db: Session = SessionLocal()
        try:
            clear_db(db)
            pipeline = IngestionPipeline(db=db, imported_by="unseen_test_user")
            pipeline.process_file(os.path.join(tmpdir, "cses.csv"))
            pipeline.process_file(os.path.join(tmpdir, "assets.csv"))
            pipeline.process_file(os.path.join(tmpdir, "analysts.csv"))
            ds_import = pipeline.process_file(os.path.join(tmpdir, "alerts.csv"))
            if os.path.exists(os.path.join(tmpdir, "maintenance_logs.csv")):
                pipeline.process_file(os.path.join(tmpdir, "maintenance_logs.csv"))

            # Ground Truth Isolation Audit: Ensure detection engine does not read ground_truth.json
            ns_engine = NegativeSpaceEngine(db=db)
            analysis_run = ns_engine.run_analysis(dataset_import_id=ds_import.id)

            assert analysis_run is not None
            assert analysis_run.status.value == "COMPLETED"

            # Perform independent ground-truth metric evaluation
            eval_report: EvaluationReport = GroundTruthEvaluator.evaluate_analysis_run(
                db=db,
                analysis_run_id=analysis_run.id,
                ground_truth_manifest_path=os.path.join(tmpdir, "ground_truth.json")
            )

            # Assert complete evaluation report metrics are computed
            assert eval_report.total_ground_truth_scenarios >= 5
            assert eval_report.true_positives >= 5
            assert eval_report.recall >= 0.80
            assert eval_report.macro_recall >= 0.80

            # Verify per-rule metrics present for all NEG rules
            neg_rules = ["NEG-01", "NEG-02", "NEG-03", "NEG-04", "NEG-05"]
            for r in neg_rules:
                assert r in eval_report.per_rule_metrics
                rm = eval_report.per_rule_metrics[r]
                assert rm.true_positives >= 1
                assert rm.recall >= 0.80
                assert hasattr(rm, "true_negatives")
                assert hasattr(rm, "false_positive_rate")

            # Verify benchmark stats in AnalysisRun configuration
            bench = analysis_run.configuration.get("benchmark", {})
            assert bench.get("records_evaluated", 0) > 0
            assert bench.get("assets_evaluated", 0) > 0
            assert bench.get("windows_evaluated", 0) > 0
            assert bench.get("records_per_second", 0.0) > 0.0

        finally:
            db.close()
