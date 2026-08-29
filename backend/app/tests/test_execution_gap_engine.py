import os
import tempfile
import time
import pytest
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import (
    Finding, Evidence, AnalysisRun, DatasetImport, Alert, Investigation, Escalation, Case, Closure, Asset, CSE, FindingStatus, FindingSeverity, AuditLog, ReviewQueueItem, RiskScore
)
from app.ingestion.generator.config import GeneratorConfig
from app.ingestion.generator.engine import SyntheticDatasetGenerator
from app.ingestion.generator.exporters import export_dataset_to_csv
from app.ingestion.pipeline import IngestionPipeline
from app.rules.service import ExecutionGapEngine
from app.analytics.evaluator import GroundTruthEvaluator


def clear_db(db: Session):
    db.query(AuditLog).delete()
    db.query(ReviewQueueItem).delete()
    db.query(RiskScore).delete()
    db.query(Evidence).delete()
    db.query(Finding).delete()
    db.query(AnalysisRun).delete()
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


def test_execution_gap_engine_detection_and_provenance():
    """Test full execution gap engine pipeline over canonical database records."""
    config = GeneratorConfig.baseline_preset()
    generator = SyntheticDatasetGenerator(config)
    dataset = generator.generate()

    with tempfile.TemporaryDirectory() as tmpdir:
        export_dataset_to_csv(dataset, tmpdir)

        db: Session = SessionLocal()
        try:
            clear_db(db)
            # 1. Ingest via Phase 4 Pipeline into Canonical DB
            pipeline = IngestionPipeline(db=db, imported_by="test_engine_user")
            pipeline.process_file(os.path.join(tmpdir, "cses.csv"))
            pipeline.process_file(os.path.join(tmpdir, "assets.csv"))
            pipeline.process_file(os.path.join(tmpdir, "analysts.csv"))
            ds_import = pipeline.process_file(os.path.join(tmpdir, "alerts.csv"))
            pipeline.process_file(os.path.join(tmpdir, "investigations.csv"))

            # 2. Execute Phase 5 Execution Gap Engine
            engine_service = ExecutionGapEngine(db=db)
            analysis_run = engine_service.run_analysis(dataset_import_id=ds_import.id)

            assert analysis_run is not None
            assert analysis_run.status.value == "COMPLETED"
            assert analysis_run.findings_generated > 0

            # 3. Verify Findings and Evidence Traceability
            findings = db.query(Finding).filter(Finding.analysis_run_id == analysis_run.id).all()
            assert len(findings) == analysis_run.findings_generated

            first_finding = findings[0]
            assert first_finding.rule_id in ("GAP-01", "GAP-03")
            assert first_finding.reason != ""
            assert first_finding.expected_behaviour != ""
            assert first_finding.observed_behaviour != ""
            assert len(first_finding.evidence_refs) > 0

            # Verify Evidence DB records
            evidence_records = db.query(Evidence).filter(Evidence.finding_id == first_finding.id).all()
            assert len(evidence_records) > 0
            assert evidence_records[0].source_table in ("alerts", "assets", "investigations")

            # 4. Evaluate Precision, Recall, F1 against synthetic ground truth
            eval_report = GroundTruthEvaluator.evaluate_analysis_run(
                db=db,
                analysis_run_id=analysis_run.id,
                ground_truth_manifest_path=os.path.join(tmpdir, "ground_truth.json")
            )
            
            assert eval_report.true_positives >= 2
            assert eval_report.recall >= 0.80
            assert eval_report.macro_recall >= 0.80

        finally:
            db.close()


def test_reproducibility():
    """Verify that re-running analysis over the same canonical data yields identical findings."""
    config = GeneratorConfig(seed=555, num_cses=3, total_alerts=200)
    generator = SyntheticDatasetGenerator(config)
    dataset = generator.generate()

    with tempfile.TemporaryDirectory() as tmpdir:
        export_dataset_to_csv(dataset, tmpdir)

        db: Session = SessionLocal()
        try:
            clear_db(db)
            pipeline = IngestionPipeline(db=db)
            pipeline.process_file(os.path.join(tmpdir, "cses.csv"))
            pipeline.process_file(os.path.join(tmpdir, "assets.csv"))
            ds_import = pipeline.process_file(os.path.join(tmpdir, "alerts.csv"))
            pipeline.process_file(os.path.join(tmpdir, "investigations.csv"))

            engine_service = ExecutionGapEngine(db=db)
            
            run1 = engine_service.run_analysis(ds_import.id)
            run2 = engine_service.run_analysis(ds_import.id)

            assert run1.findings_generated == run2.findings_generated
        finally:
            db.close()
