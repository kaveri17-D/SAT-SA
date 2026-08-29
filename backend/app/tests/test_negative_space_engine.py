import os
import tempfile
import time
import uuid
from datetime import datetime, timedelta, timezone
import pytest
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import (
    Finding, Evidence, AnalysisRun, DatasetImport, Alert, Investigation, MaintenanceLog, Asset, CSE,
    AssetCriticality, AlertSeverity, FindingStatus, FindingSeverity, AuditLog, ReviewQueueItem, RiskScore
)
from app.ingestion.generator.config import GeneratorConfig
from app.ingestion.generator.engine import SyntheticDatasetGenerator
from app.ingestion.generator.exporters import export_dataset_to_csv
from app.ingestion.pipeline import IngestionPipeline
from app.rules.negative_space import NegativeSpaceEvaluators
from app.rules.matrix import ExpectedEvidenceMatrix, ExpectedEvidenceRule
from app.rules.evaluator import EvaluationStatus
from app.rules.service import NegativeSpaceEngine
from app.analytics.evaluator import GroundTruthEvaluator


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


def test_neg01_missing_telemetry_detection_and_suppression():
    """Verify NEG-01 detection, maintenance suppression, decommissioned suppression, and low quality downgrade."""
    now = datetime.now(timezone.utc)
    cse = CSE(id=uuid.uuid4(), name="Test CSE", sector="ENERGY", entity_type="GRID_OPERATOR", size_tier="TIER_1")
    
    asset_active = Asset(id=uuid.uuid4(), cse_id=cse.id, name="Active-SCADA", asset_type="SCADA_CONTROLLER", criticality=AssetCriticality.CRITICAL, status="ACTIVE")
    asset_decom = Asset(id=uuid.uuid4(), cse_id=cse.id, name="Decom-SCADA", asset_type="SCADA_CONTROLLER", criticality=AssetCriticality.CRITICAL, status="DECOMMISSIONED", decommissioned_at=now)
    asset_maint = Asset(id=uuid.uuid4(), cse_id=cse.id, name="Maint-SCADA", asset_type="SCADA_CONTROLLER", criticality=AssetCriticality.CRITICAL, status="ACTIVE")

    maint_log = MaintenanceLog(id=uuid.uuid4(), cse_id=cse.id, asset_id=asset_maint.id, maintenance_ref="MAINT_01", start_time=now - timedelta(days=1), end_time=now + timedelta(days=1), reason="Scheduled maintenance")

    # 1. Positive detection for active asset with 0 telemetry
    res_pos = NegativeSpaceEvaluators.evaluate_neg01_missing_telemetry(asset=asset_active, recent_alerts=[], maintenance_logs=[], evaluation_timestamp=now)
    assert res_pos.status == EvaluationStatus.CONFIRMED
    assert res_pos.confidence == 0.95
    assert len(res_pos.evidence_refs) > 0

    # 2. Legitimate Maintenance suppression
    res_maint = NegativeSpaceEvaluators.evaluate_neg01_missing_telemetry(asset=asset_maint, recent_alerts=[], maintenance_logs=[maint_log], evaluation_timestamp=now)
    assert res_maint.status == EvaluationStatus.SUPPRESSED

    # 3. Decommissioned suppression
    res_decom = NegativeSpaceEvaluators.evaluate_neg01_missing_telemetry(asset=asset_decom, recent_alerts=[], maintenance_logs=[], evaluation_timestamp=now)
    assert res_decom.status == EvaluationStatus.SUPPRESSED

    # 4. Poor data quality downgrade (<50% completeness score -> UNKNOWN)
    res_poor = NegativeSpaceEvaluators.evaluate_neg01_missing_telemetry(asset=asset_active, recent_alerts=[], maintenance_logs=[], completeness_score=40.0, evaluation_timestamp=now)
    assert res_poor.status == EvaluationStatus.UNKNOWN


def test_neg02_telemetry_drop_rolling_baseline():
    """Verify NEG-02 30-day time series baseline calculation and sudden drop detection."""
    now = datetime.now(timezone.utc)
    cse = CSE(id=uuid.uuid4(), name="Telecom CSE", sector="TELECOM", entity_type="OPERATOR", size_tier="TIER_1")
    
    # 1. Full 30 days of baseline alerts (from 2 days ago to 30 days ago)
    alerts = []
    for day in range(2, 30):
        for _ in range(10):
            alerts.append(Alert(id=uuid.uuid4(), cse_id=cse.id, source_system="SIEM", category="MALWARE_DETECTION", severity=AlertSeverity.HIGH, created_at=now - timedelta(days=day)))

    # Day 0 (recent 24h) has 0 alerts -> 100% drop from ~10/day baseline
    res = NegativeSpaceEvaluators.evaluate_neg02_telemetry_drop(cse=cse, alerts=alerts, evaluation_timestamp=now)
    assert res.status == EvaluationStatus.CONFIRMED
    assert res.baseline["mean_daily_volume"] > 5.0
    assert res.absence_deviation_measurement != ""


def test_neg03_missing_category_matrix():
    """Verify NEG-03 expected evidence matrix matching."""
    cse = CSE(id=uuid.uuid4(), name="Power CSE", sector="ENERGY", entity_type="GRID_OPERATOR", size_tier="TIER_1")
    matrix = ExpectedEvidenceMatrix()

    # Alerts present, but zero MALWARE_DETECTION
    alerts = [
        Alert(id=uuid.uuid4(), cse_id=cse.id, source_system="SIEM", category="AUTHENTICATION_FAILURE", severity=AlertSeverity.LOW, created_at=datetime.now(timezone.utc))
    ]

    res = NegativeSpaceEvaluators.evaluate_neg03_missing_category(cse=cse, alerts=alerts, expected_category="MALWARE_DETECTION", matrix=matrix)
    assert res.status == EvaluationStatus.CONFIRMED
    assert "MALWARE_DETECTION" in res.explanation


def test_neg04_critical_asset_under_monitoring():
    """Verify NEG-04 peer group baseline comparison for under-monitored asset."""
    cse = CSE(id=uuid.uuid4(), name="Grid CSE", sector="ENERGY", entity_type="OPERATOR", size_tier="TIER_1")
    
    target_asset = Asset(id=uuid.uuid4(), cse_id=cse.id, name="Target-SCADA", asset_type="SCADA_CONTROLLER", criticality=AssetCriticality.CRITICAL, status="ACTIVE")
    peer1 = Asset(id=uuid.uuid4(), cse_id=cse.id, name="Peer1-SCADA", asset_type="SCADA_CONTROLLER", criticality=AssetCriticality.CRITICAL, status="ACTIVE")
    peer2 = Asset(id=uuid.uuid4(), cse_id=cse.id, name="Peer2-SCADA", asset_type="SCADA_CONTROLLER", criticality=AssetCriticality.CRITICAL, status="ACTIVE")

    all_assets = [target_asset, peer1, peer2]

    # Target has 1 alert, peers have 20 alerts each
    all_alerts = [Alert(id=uuid.uuid4(), cse_id=cse.id, asset_id=target_asset.id, source_system="SIEM", category="PORT_SCAN", severity=AlertSeverity.LOW, created_at=datetime.now(timezone.utc))]
    for _ in range(20):
        all_alerts.append(Alert(id=uuid.uuid4(), cse_id=cse.id, asset_id=peer1.id, source_system="SIEM", category="PORT_SCAN", severity=AlertSeverity.LOW, created_at=datetime.now(timezone.utc)))
        all_alerts.append(Alert(id=uuid.uuid4(), cse_id=cse.id, asset_id=peer2.id, source_system="SIEM", category="PORT_SCAN", severity=AlertSeverity.LOW, created_at=datetime.now(timezone.utc)))

    res = NegativeSpaceEvaluators.evaluate_neg04_under_monitored_asset(target_asset=target_asset, all_assets=all_assets, all_alerts=all_alerts)
    assert res.status == EvaluationStatus.CONFIRMED
    assert res.baseline["peer_median_density"] == 20.0


def test_neg05_unexplained_maintenance_silence():
    """Verify NEG-05 state distinctions: MAINTENANCE_EXPLAINED vs MAINTENANCE_NOT_RECORDED."""
    now = datetime.now(timezone.utc)
    cse = CSE(id=uuid.uuid4(), name="Grid CSE", sector="ENERGY", entity_type="OPERATOR", size_tier="TIER_1")
    asset = Asset(id=uuid.uuid4(), cse_id=cse.id, name="Node-01", asset_type="SCADA_CONTROLLER", criticality=AssetCriticality.CRITICAL, status="ACTIVE")

    maint_log = MaintenanceLog(id=uuid.uuid4(), cse_id=cse.id, asset_id=asset.id, maintenance_ref="MAINT_100", start_time=now - timedelta(days=1), end_time=now + timedelta(days=1), reason="Firmware upgrade")

    # 1. Silence WITH authorized maintenance log -> MAINTENANCE_EXPLAINED (SUPPRESSED)
    res_explained = NegativeSpaceEvaluators.evaluate_neg05_unexplained_maintenance_silence(asset=asset, recent_alerts=[], maintenance_logs=[maint_log], evaluation_timestamp=now)
    assert res_explained.status == EvaluationStatus.SUPPRESSED
    assert "MAINTENANCE_EXPLAINED" in res_explained.explanation

    # 2. Silence WITHOUT authorized maintenance log -> MAINTENANCE_NOT_RECORDED (CONFIRMED Finding)
    res_unexplained = NegativeSpaceEvaluators.evaluate_neg05_unexplained_maintenance_silence(asset=asset, recent_alerts=[], maintenance_logs=[], evaluation_timestamp=now)
    assert res_unexplained.status == EvaluationStatus.CONFIRMED
    assert "MAINTENANCE_NOT_RECORDED" in res_unexplained.explanation


def test_full_negative_space_engine_pipeline_and_benchmark():
    """Test full Negative Space Engine ingestion, execution, DB findings, benchmark, and per-rule evaluation report."""
    config = GeneratorConfig.baseline_preset()
    generator = SyntheticDatasetGenerator(config)
    dataset = generator.generate()

    with tempfile.TemporaryDirectory() as tmpdir:
        export_dataset_to_csv(dataset, tmpdir)

        db: Session = SessionLocal()
        try:
            clear_db(db)
            pipeline = IngestionPipeline(db=db, imported_by="test_neg_user")
            pipeline.process_file(os.path.join(tmpdir, "cses.csv"))
            pipeline.process_file(os.path.join(tmpdir, "assets.csv"))
            pipeline.process_file(os.path.join(tmpdir, "analysts.csv"))
            ds_import = pipeline.process_file(os.path.join(tmpdir, "alerts.csv"))

            # Execute NegativeSpaceEngine
            engine = NegativeSpaceEngine(db=db)
            analysis_run = engine.run_analysis(dataset_import_id=ds_import.id)

            assert analysis_run is not None
            assert analysis_run.status.value == "COMPLETED"
            assert analysis_run.findings_generated > 0

            benchmark = analysis_run.configuration.get("benchmark", {})
            assert benchmark["records_evaluated"] > 0
            assert benchmark["assets_evaluated"] > 0
            assert benchmark["execution_time_seconds"] >= 0.0

            # Verify Findings and Evidence in canonical DB
            findings = db.query(Finding).filter(Finding.analysis_run_id == analysis_run.id).all()
            assert len(findings) == analysis_run.findings_generated

            evidence_records = db.query(Evidence).all()
            assert len(evidence_records) > 0

            # Evaluate per-rule Precision, Recall, F1
            report = GroundTruthEvaluator.evaluate_analysis_run(
                db=db,
                analysis_run_id=analysis_run.id,
                ground_truth_manifest_path=os.path.join(tmpdir, "ground_truth.json")
            )

            assert report.true_positives > 0
            assert "NEG-01" in report.per_rule_metrics or "NEG-02" in report.per_rule_metrics or "NEG-03" in report.per_rule_metrics
            assert report.macro_precision >= 0.0
            assert report.macro_recall >= 0.0

        finally:
            db.close()
