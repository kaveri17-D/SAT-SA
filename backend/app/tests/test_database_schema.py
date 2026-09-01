import uuid
from datetime import datetime, timezone
import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.core.database import Base, engine, SessionLocal
import app.models
from app.models import (
    Base, CSE, Asset, Alert, Investigation, Analyst, Escalation, Case, Closure, MaintenanceLog,
    DatasetImport, DataQualityIssue, RuleVersion, ModelVersion, AnalysisRun, AuditLog,
    Finding, Evidence, RiskScore, PeerGroup, PeerGroupMembership, Benchmark,
    AssetCriticality, AlertSeverity, FindingSeverity, FindingStatus, AnalysisRunStatus,
    DatasetImportStatus, VersionStatus, DataQualitySeverity, DispositionType
)
from app.db.seed import seed_baseline_reference_data


def test_schema_entities_count():
    """Verify that all 24 entities exist in SQLAlchemy metadata."""
    Base.metadata.create_all(bind=engine)
    tables = Base.metadata.tables
    expected_tables = {
        "cses", "assets", "alerts", "investigations", "analysts", "escalations",
        "cases", "closures", "maintenance_logs", "dataset_imports", "data_quality_issues", "rule_versions",
        "model_versions", "analysis_runs", "audit_logs", "findings", "evidence",
        "risk_scores", "peer_groups", "peer_group_memberships", "benchmarks", "review_queue_items",
        "report_snapshots", "report_evidence_references"
    }
    assert len(tables) == 24
    assert set(tables.keys()) == expected_tables


def test_seed_baseline_reference_data():
    """Test seeding baseline rules and model versions into database."""
    db: Session = SessionLocal()
    try:
        seed_baseline_reference_data(db)
        
        rule_count = db.query(RuleVersion).count()
        assert rule_count >= 9
        
        model_count = db.query(ModelVersion).count()
        assert model_count >= 2
        
        gap01 = db.query(RuleVersion).filter(RuleVersion.rule_id == "GAP-01").first()
        assert gap01 is not None
        assert gap01.name == "Critical Alert Closed Without Escalation"
        assert gap01.status == VersionStatus.ACTIVE
    finally:
        db.close()


def test_provenance_chain_integrity():
    """Test provenance traceability: DatasetImport -> AnalysisRun -> Finding -> Evidence."""
    db: Session = SessionLocal()
    try:
        # 1. Create CSE & Asset
        unique_name = f"Test Supervisory Energy Corp {uuid.uuid4()}"
        cse = CSE(name=unique_name, sector="ENERGY", entity_type="POWER_GRID", size_tier="TIER_1")
        db.add(cse)
        db.flush()

        asset = Asset(cse_id=cse.id, name="Substation SCADA Master", asset_type="SCADA", criticality=AssetCriticality.CRITICAL)
        db.add(asset)
        db.flush()

        # 2. Create DatasetImport & AnalysisRun
        ds_import = DatasetImport(
            filename="soc_exports_energy_q1.csv",
            source="NCIIPC_SECURE_INGEST",
            imported_by="examiner_01",
            row_count=5000,
            status=DatasetImportStatus.COMPLETED,
            completeness_score=98.5
        )
        db.add(ds_import)
        db.flush()

        analysis_run = AnalysisRun(
            dataset_import_id=ds_import.id,
            started_at=datetime.now(timezone.utc),
            status=AnalysisRunStatus.COMPLETED,
            records_processed=5000,
            findings_generated=1,
            rule_version="1.0.0",
            model_version="1.0.0"
        )
        db.add(analysis_run)
        db.flush()

        # 3. Create Finding linked to AnalysisRun
        finding = Finding(
            analysis_run_id=analysis_run.id,
            cse_id=cse.id,
            asset_id=asset.id,
            rule_id="GAP-01",
            rule_version="1.0.0",
            severity=FindingSeverity.CRITICAL,
            anomaly_score=0.92,
            confidence=0.98,
            risk_score=85.0,
            supervisory_priority=90.0,
            reason="Critical alert closed without escalation record.",
            expected_behaviour="Critical alerts must be escalated within 30 minutes.",
            observed_behaviour="Alert closed after 5 minutes without escalation.",
            evidence_refs=[{"table": "alerts", "id": str(uuid.uuid4())}],
            recommendation="Review analyst closure procedure and verify SCADA integrity.",
            status=FindingStatus.NEW
        )
        db.add(finding)
        db.flush()

        # 4. Create Evidence linked to Finding
        evidence = Evidence(
            finding_id=finding.id,
            evidence_type="RAW_ALERT_RECORD",
            source_table="alerts",
            source_record_id="alt-9901",
            description="Alert ALT-9901 CRITICAL severity with zero escalation."
        )
        db.add(evidence)
        db.flush()

        # 5. Create RiskScore referencing AnalysisRun
        risk_score = RiskScore(
            cse_id=cse.id,
            analysis_run_id=analysis_run.id,
            total_score=85.0,
            component_breakdown={
                "execution_gap": 30.0,
                "negative_space": 25.0,
                "peer_deviation": 20.0,
                "inv_anomaly": 10.0,
                "asset_criticality": 0.0
            },
            rule_version="1.0.0",
            model_version="1.0.0"
        )
        db.add(risk_score)
        db.commit()

        # Provenance verification assertions
        queried_finding = db.query(Finding).filter(Finding.id == finding.id).first()
        assert queried_finding is not None
        assert queried_finding.analysis_run_id == analysis_run.id
        assert queried_finding.analysis_run.dataset_import_id == ds_import.id
        assert len(queried_finding.evidence_records) == 1
        assert queried_finding.evidence_records[0].source_record_id == "alt-9901"

        queried_risk = db.query(RiskScore).filter(RiskScore.analysis_run_id == analysis_run.id).first()
        assert queried_risk is not None
        assert queried_risk.total_score == 85.0
        assert queried_risk.component_breakdown["execution_gap"] == 30.0

    finally:
        db.close()
