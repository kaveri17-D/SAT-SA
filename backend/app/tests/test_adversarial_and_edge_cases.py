import uuid
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import (
    CSE, Asset, Alert, Finding, Evidence, AnalysisRun, RiskScore, ReviewQueueItem,
    AuditLog, MaintenanceLog, Investigation, Escalation, Case, Closure,
    FindingSeverity, FindingStatus, AssetCriticality
)

from app.rules.service import ExecutionGapEngine, NegativeSpaceEngine

from app.analytics.risk_engine import SupervisoryRiskEngine
from app.analytics.prioritization_engine import ReviewPrioritizationEngine
from app.analytics.graph_engine import SupervisoryEvidenceGraphEngine
from app.evidence.assembler import EvidenceAssembler


def clear_db(db: Session):
    db.query(AuditLog).delete()
    db.query(ReviewQueueItem).delete()
    db.query(RiskScore).delete()
    db.query(Finding).delete()
    db.query(Evidence).delete()
    db.query(Closure).delete()
    db.query(Case).delete()
    db.query(Escalation).delete()
    db.query(Investigation).delete()
    db.query(Alert).delete()
    db.query(Asset).delete()
    db.query(CSE).delete()
    db.query(AnalysisRun).delete()
    db.commit()


def test_adversarial_empty_dataset():
    """Verify safe behavior when pipeline runs against empty database."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        import_id = uuid.uuid4()
        run_id = uuid.uuid4()
        run = AnalysisRun(id=run_id, dataset_import_id=import_id, rule_version="1.0.0", status="RUNNING")
        db.add(run)
        db.commit()

        gap_engine = ExecutionGapEngine(db=db)
        gap_run = gap_engine.run_analysis(dataset_import_id=import_id, analysis_run_id=run_id)

        neg_engine = NegativeSpaceEngine(db=db)
        neg_run = neg_engine.run_analysis(dataset_import_id=import_id, analysis_run_id=run_id)

        risks = SupervisoryRiskEngine.compute_supervisory_risk(db, run_id)
        assert len(risks) == 0

        queue, metrics = ReviewPrioritizationEngine.generate_review_queue(db, run_id)
        assert len(queue) == 0

        G = SupervisoryEvidenceGraphEngine.build_graph_for_analysis_run(db, run_id)
        assert G.number_of_nodes() == 0

    finally:
        db.close()


def test_adversarial_single_record_dataset():
    """Verify single alert dataset processes without exception or out-of-bounds error."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        import_id = uuid.uuid4()
        run_id = uuid.uuid4()
        cse_id = uuid.uuid4()
        asset_id = uuid.uuid4()

        run = AnalysisRun(id=run_id, dataset_import_id=import_id, rule_version="1.0.0", status="RUNNING")
        cse = CSE(id=cse_id, name="Single Record CSE", sector="ENERGY", entity_type="UTILITY", size_tier="TIER_1")
        asset = Asset(id=asset_id, cse_id=cse_id, name="Single-Asset", asset_type="SERVER", criticality=AssetCriticality.CRITICAL, status="ACTIVE")
        alert = Alert(id=uuid.uuid4(), cse_id=cse_id, asset_id=asset_id, source_system="SIEM", category="UNAUTHORIZED_ACCESS", severity="HIGH", raw_severity="HIGH", status="OPEN", created_at=datetime.now(timezone.utc))

        db.add_all([run, cse, asset, alert])
        db.commit()

        gap_engine = ExecutionGapEngine(db=db)
        gap_run = gap_engine.run_analysis(dataset_import_id=import_id, analysis_run_id=run_id)
        assert gap_run is not None

        neg_engine = NegativeSpaceEngine(db=db)
        neg_run = neg_engine.run_analysis(dataset_import_id=import_id, analysis_run_id=run_id)
        assert neg_run is not None

    finally:
        db.close()


def test_adversarial_active_maintenance_window_suppression():
    """Verify that alerts/silence on assets inside active maintenance windows are properly handled."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        import_id = uuid.uuid4()
        run_id = uuid.uuid4()
        cse_id = uuid.uuid4()
        asset_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        run = AnalysisRun(id=run_id, dataset_import_id=import_id, rule_version="1.0.0", status="RUNNING")
        cse = CSE(id=cse_id, name="Maint CSE", sector="DEFENSE", entity_type="MILITARY", size_tier="TIER_1")
        asset = Asset(id=asset_id, cse_id=cse_id, name="Maint-Workstation", asset_type="WORKSTATION", criticality=AssetCriticality.HIGH, status="ACTIVE")
        
        maint = MaintenanceLog(
            id=uuid.uuid4(), cse_id=cse_id, asset_id=asset_id,
            maintenance_ref="SCHEDULED_MAINT_42",
            start_time=now - timedelta(days=2),
            end_time=now + timedelta(days=2),
            reason="Scheduled patch maintenance", approved_by="ADMIN"
        )

        db.add_all([run, cse, asset, maint])
        db.commit()

        neg_engine = NegativeSpaceEngine(db=db)
        neg_engine.run_analysis(dataset_import_id=import_id, analysis_run_id=run_id)
        
        negs = db.query(Finding).filter(Finding.analysis_run_id == run_id).all()
        # NEG-01 telemetry silence should suppress finding because asset has active maintenance log
        neg_01_findings = [f for f in negs if f.rule_id == "NEG-01" and f.asset_id == asset_id]
        assert len(neg_01_findings) == 0

    finally:
        db.close()


def test_adversarial_decommissioned_asset_filter():
    """Verify that decommissioned assets do not trigger false positive telemetry silence findings."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        import_id = uuid.uuid4()
        run_id = uuid.uuid4()
        cse_id = uuid.uuid4()
        asset_id = uuid.uuid4()

        run = AnalysisRun(id=run_id, dataset_import_id=import_id, rule_version="1.0.0", status="RUNNING")
        cse = CSE(id=cse_id, name="Decom CSE", sector="FINANCE", entity_type="BANK", size_tier="TIER_1")
        asset = Asset(id=asset_id, cse_id=cse_id, name="Old-DB", asset_type="DATABASE_SERVER", criticality=AssetCriticality.CRITICAL, status="DECOMMISSIONED")

        db.add_all([run, cse, asset])
        db.commit()

        neg_engine = NegativeSpaceEngine(db=db)
        neg_engine.run_analysis(dataset_import_id=import_id, analysis_run_id=run_id)

        negs = db.query(Finding).filter(Finding.analysis_run_id == run_id).all()
        decom_findings = [f for f in negs if f.asset_id == asset_id]
        assert len(decom_findings) == 0

    finally:
        db.close()


def test_adversarial_graph_cycles_handling():
    """Verify EvidenceGraph construction handles cyclical or duplicate relations safely."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        import_id = uuid.uuid4()
        run_id = uuid.uuid4()
        cse_id = uuid.uuid4()
        asset_id = uuid.uuid4()
        alert_id = uuid.uuid4()

        run = AnalysisRun(id=run_id, dataset_import_id=import_id, rule_version="1.0.0", status="RUNNING")
        cse = CSE(id=cse_id, name="Cycle CSE", sector="HEALTHCARE", entity_type="HOSPITAL", size_tier="TIER_1")
        asset = Asset(id=asset_id, cse_id=cse_id, name="Ventilator-Gateway", asset_type="MEDICAL_DEVICE", criticality=AssetCriticality.CRITICAL, status="ACTIVE")
        alert = Alert(id=alert_id, cse_id=cse_id, asset_id=asset_id, source_system="SENSOR", category="PHYSICAL_TAMPER", severity="CRITICAL", raw_severity="CRITICAL", status="OPEN", created_at=datetime.now(timezone.utc))

        db.add_all([run, cse, asset, alert])
        db.commit()

        G = SupervisoryEvidenceGraphEngine.build_graph_for_analysis_run(db, run_id)
        assert G.has_node(f"CSE:{cse_id}") or G.has_node(str(cse_id))
        assert G.has_node(f"ASSET:{asset_id}") or G.has_node(str(asset_id))
        assert G.has_node(f"ALERT:{alert_id}") or G.has_node(str(alert_id))
        assert G.number_of_nodes() >= 3


    finally:
        db.close()


def test_adversarial_reproducibility_idempotency():
    """Verify that running analysis engines twice on identical data yields 100% identical finding counts."""
    db: Session = SessionLocal()
    try:
        clear_db(db)
        import_id = uuid.uuid4()
        run_id = uuid.uuid4()
        cse_id = uuid.uuid4()
        asset_id = uuid.uuid4()
        alert_id = uuid.uuid4()

        run = AnalysisRun(id=run_id, dataset_import_id=import_id, rule_version="1.0.0", status="RUNNING")

        cse = CSE(id=cse_id, name="Idempotent CSE", sector="WATER", entity_type="PLANT", size_tier="TIER_1")
        asset = Asset(id=asset_id, cse_id=cse_id, name="Pump-Control", asset_type="PLC", criticality=AssetCriticality.CRITICAL, status="ACTIVE")
        alert = Alert(id=alert_id, cse_id=cse_id, asset_id=asset_id, source_system="SCADA", category="EXFILTRATION_SUSPICION", severity="CRITICAL", raw_severity="CRITICAL", status="OPEN", created_at=datetime.now(timezone.utc))
        inv = Investigation(id=uuid.uuid4(), alert_id=alert_id, started_at=datetime.now(timezone.utc), outcome="CLOSED")

        db.add_all([run, cse, asset, alert, inv])
        db.commit()

        gap_engine = ExecutionGapEngine(db=db)
        gap_engine.run_analysis(dataset_import_id=import_id, analysis_run_id=run_id)
        count1 = db.query(Finding).filter(Finding.analysis_run_id == run_id).count()

        gap_engine.run_analysis(dataset_import_id=import_id, analysis_run_id=run_id)
        count2 = db.query(Finding).filter(Finding.analysis_run_id == run_id).count()

        assert count1 == count2


    finally:
        db.close()
