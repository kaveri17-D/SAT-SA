import os
import tempfile
import uuid
import time
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi.testclient import TestClient

from app.core.database import SessionLocal, Base, engine
from app.models import (
    CSE, Asset, Alert, Investigation, Analyst, Escalation, Case, Closure, MaintenanceLog,
    AnalysisRun, RiskScore, ReviewQueueItem, AuditLog, DatasetImport, Finding, Evidence,
    AssetCriticality, AlertSeverity, FindingSeverity, FindingStatus, DispositionType, DatasetImportStatus
)
from app.ingestion.generator.config import GeneratorConfig
from app.ingestion.generator.engine import SyntheticDatasetGenerator
from app.ingestion.generator.exporters import export_dataset_to_csv
from app.ingestion.pipeline import IngestionPipeline
from app.analytics.graph_engine import SupervisoryEvidenceGraphEngine
from app.main import app as fastapi_app


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
    db.query(MaintenanceLog).delete()
    db.query(Alert).delete()
    db.query(Asset).delete()
    db.query(Analyst).delete()
    db.query(CSE).delete()
    db.query(DatasetImport).delete()
    db.commit()
    db.expire_all()


def test_basic_graph_construction():
    """Test graph construction containing all node and edge types."""
    db: Session = SessionLocal()
    try:
        clear_db(db)

        cse = CSE(id=uuid.uuid4(), name="PowerGrid North", sector="ENERGY", entity_type="CRITICAL_INFRASTRUCTURE", size_tier="TIER_1")
        asset = Asset(id=uuid.uuid4(), cse_id=cse.id, name="SCADA Master", asset_type="CONTROL_SYSTEM", criticality=AssetCriticality.CRITICAL, status="ACTIVE")
        analyst = Analyst(id=uuid.uuid4(), cse_id=cse.id, handle="Examiner A", role="SENIOR_ANALYST")

        db.add_all([cse, asset, analyst])
        db.commit()

        run_id = uuid.uuid4()
        G = SupervisoryEvidenceGraphEngine.build_graph_for_analysis_run(db, run_id)

        assert G.number_of_nodes() >= 3
        assert G.has_node(f"CSE:{cse.id}")
        assert G.has_node(f"ASSET:{asset.id}")
        assert G.has_node(f"ANALYST:{analyst.id}")
        assert G.has_edge(f"CSE:{cse.id}", f"ASSET:{asset.id}")
        assert G.edges[f"CSE:{cse.id}", f"ASSET:{asset.id}"]["relationship"] == "OWNS"
    finally:
        db.close()


def test_workflow_path_reconstruction():
    """Test expected vs observed workflow path reconstruction."""
    db: Session = SessionLocal()
    try:
        clear_db(db)

        cse = CSE(id=uuid.uuid4(), name="Grid West", sector="ENERGY", entity_type="CRITICAL_INFRASTRUCTURE", size_tier="TIER_1")
        asset = Asset(id=uuid.uuid4(), cse_id=cse.id, name="Substation Alpha", asset_type="SUBSTATION", criticality=AssetCriticality.CRITICAL, status="ACTIVE")
        alt = Alert(id=uuid.uuid4(), cse_id=cse.id, asset_id=asset.id, source_system="SIEM", category="UNAUTHORIZED_ACCESS", severity=AlertSeverity.CRITICAL, raw_severity="CRITICAL", created_at=datetime.now(timezone.utc))
        inv = Investigation(id=uuid.uuid4(), alert_id=alt.id, started_at=datetime.now(timezone.utc) + timedelta(minutes=5), duration_seconds=1800)
        esc = Escalation(id=uuid.uuid4(), investigation_id=inv.id, escalated_to="EXAMINER_TIER_2", escalated_at=datetime.now(timezone.utc) + timedelta(minutes=10), reason="Critical threat")
        c = Case(id=uuid.uuid4(), cse_id=cse.id, opened_at=datetime.now(timezone.utc) + timedelta(minutes=15), status="OPEN")
        clo = Closure(id=uuid.uuid4(), case_id=c.id, disposition_type=DispositionType.TRUE_POSITIVE, closed_at=datetime.now(timezone.utc) + timedelta(minutes=60), closed_by="Examiner A")

        db.add_all([cse, asset, alt, inv, esc, c, clo])
        db.commit()

        run_id = uuid.uuid4()
        G = SupervisoryEvidenceGraphEngine.build_graph_for_analysis_run(db, run_id)

        path_info = SupervisoryEvidenceGraphEngine.reconstruct_alert_path(G, alt.id)

        assert path_info["alert_id"] == str(alt.id)
        assert path_info["severity"] == "CRITICAL"
        assert path_info["expected_path"] == ["ALERT", "INVESTIGATION", "ESCALATION", "CASE", "CLOSURE"]
        assert path_info["observed_sequence"] == ["ALERT", "INVESTIGATION", "ESCALATION", "CASE", "CLOSURE"]
        assert path_info["missing_transitions"] == []
        assert path_info["is_anomalous"] is False
    finally:
        db.close()


def test_missing_escalation_detection():
    """Test detection of missing escalation transition for critical alerts."""
    db: Session = SessionLocal()
    try:
        clear_db(db)

        cse = CSE(id=uuid.uuid4(), name="Grid West", sector="ENERGY", entity_type="CRITICAL_INFRASTRUCTURE", size_tier="TIER_1")
        asset = Asset(id=uuid.uuid4(), cse_id=cse.id, name="Substation Alpha", asset_type="SUBSTATION", criticality=AssetCriticality.CRITICAL, status="ACTIVE")
        alt = Alert(id=uuid.uuid4(), cse_id=cse.id, asset_id=asset.id, source_system="SIEM", category="UNAUTHORIZED_ACCESS", severity=AlertSeverity.CRITICAL, raw_severity="CRITICAL", created_at=datetime.now(timezone.utc))
        inv = Investigation(id=uuid.uuid4(), alert_id=alt.id, started_at=datetime.now(timezone.utc) + timedelta(minutes=5), duration_seconds=1800)
        c = Case(id=uuid.uuid4(), cse_id=cse.id, opened_at=datetime.now(timezone.utc) + timedelta(minutes=15), status="OPEN")

        db.add_all([cse, asset, alt, inv, c])
        db.commit()

        run_id = uuid.uuid4()
        G = SupervisoryEvidenceGraphEngine.build_graph_for_analysis_run(db, run_id)

        path_info = SupervisoryEvidenceGraphEngine.reconstruct_alert_path(G, alt.id)

        assert path_info["is_anomalous"] is True
        assert len(path_info["missing_transitions"]) == 1
        assert path_info["missing_transitions"][0]["from"] == "INVESTIGATION"
        assert path_info["missing_transitions"][0]["to"] == "ESCALATION"
    finally:
        db.close()


def test_orphan_entity_detection():
    """Test detection of orphan workflow entities with in_degree == 0."""
    db: Session = SessionLocal()
    try:
        clear_db(db)

        cse = CSE(id=uuid.uuid4(), name="Grid East", sector="ENERGY", entity_type="CRITICAL_INFRASTRUCTURE", size_tier="TIER_1")
        unlinked_inv = Investigation(id=uuid.uuid4(), alert_id=uuid.uuid4(), started_at=datetime.now(timezone.utc), duration_seconds=600)

        db.add_all([cse, unlinked_inv])
        db.commit()

        run_id = uuid.uuid4()
        G = SupervisoryEvidenceGraphEngine.build_graph_for_analysis_run(db, run_id)

        anomalies = SupervisoryEvidenceGraphEngine.detect_graph_anomalies(db, G, run_id)
        orphan_anomalies = [a for a in anomalies if a["anomaly_type"] == "ORPHAN_ENTITY"]

        assert len(orphan_anomalies) >= 1
        assert orphan_anomalies[0]["source_node"] == f"INVESTIGATION:{unlinked_inv.id}"
    finally:
        db.close()


def test_temporal_sequence_validation():
    """Test timestamp ordering validation and impossible sequence detection."""
    db: Session = SessionLocal()
    try:
        clear_db(db)

        cse = CSE(id=uuid.uuid4(), name="Grid East", sector="ENERGY", entity_type="CRITICAL_INFRASTRUCTURE", size_tier="TIER_1")
        asset = Asset(id=uuid.uuid4(), cse_id=cse.id, name="RTU Unit", asset_type="CONTROL_SYSTEM", criticality=AssetCriticality.HIGH, status="ACTIVE")

        now = datetime.now(timezone.utc)
        alt = Alert(id=uuid.uuid4(), cse_id=cse.id, asset_id=asset.id, source_system="SIEM", category="MALWARE", severity=AlertSeverity.HIGH, raw_severity="HIGH", created_at=now)
        # Investigation started BEFORE alert created -> Temporal Violation
        inv = Investigation(id=uuid.uuid4(), alert_id=alt.id, started_at=now - timedelta(hours=2), duration_seconds=1200)

        db.add_all([cse, asset, alt, inv])
        db.commit()

        run_id = uuid.uuid4()
        G = SupervisoryEvidenceGraphEngine.build_graph_for_analysis_run(db, run_id)

        valid_temp, violations = SupervisoryEvidenceGraphEngine.validate_temporal_sequence(G, alt.id)

        assert valid_temp is False
        assert len(violations) == 1
        assert "prior to Alert created_at" in violations[0]
    finally:
        db.close()


def test_negative_space_representation():
    """Test explicit MISSING_EXPECTED graph node creation for silent critical assets."""
    db: Session = SessionLocal()
    try:
        clear_db(db)

        cse = CSE(id=uuid.uuid4(), name="Grid Silent", sector="ENERGY", entity_type="CRITICAL_INFRASTRUCTURE", size_tier="TIER_1")
        silent_critical_asset = Asset(id=uuid.uuid4(), cse_id=cse.id, name="Nuclear Turbine Master", asset_type="CRITICAL_CONTROL", criticality=AssetCriticality.CRITICAL, status="ACTIVE")

        db.add_all([cse, silent_critical_asset])
        db.commit()

        run_id = uuid.uuid4()
        G = SupervisoryEvidenceGraphEngine.build_graph_for_analysis_run(db, run_id)

        missing_node = f"MISSING_EXPECTED:{silent_critical_asset.id}"
        assert G.has_node(missing_node)
        assert G.nodes[missing_node]["entity_type"] == "MISSING_EXPECTED"
        assert G.has_edge(f"ASSET:{silent_critical_asset.id}", missing_node)
        assert G.edges[f"ASSET:{silent_critical_asset.id}", missing_node]["relationship"] == "MISSING_EXPECTED"

        anomalies = SupervisoryEvidenceGraphEngine.detect_graph_anomalies(db, G, run_id)
        neg_space_anomalies = [a for a in anomalies if a["anomaly_type"] == "MISSING_EXPECTED_ACTIVITY"]

        assert len(neg_space_anomalies) == 1
        assert neg_space_anomalies[0]["source_node"] == missing_node
    finally:
        db.close()


def test_adversarial_non_anomalies():
    """Adversarial Test: Optional escalation on non-critical alert & small analyst team should NOT become anomalous."""
    db: Session = SessionLocal()
    try:
        clear_db(db)

        cse = CSE(id=uuid.uuid4(), name="Grid Normal", sector="ENERGY", entity_type="CRITICAL_INFRASTRUCTURE", size_tier="TIER_1")
        asset = Asset(id=uuid.uuid4(), cse_id=cse.id, name="Log Relay", asset_type="SERVER", criticality=AssetCriticality.LOW, status="ACTIVE")
        alt = Alert(id=uuid.uuid4(), cse_id=cse.id, asset_id=asset.id, source_system="SYSLOG", category="PORT_SCAN", severity=AlertSeverity.LOW, raw_severity="LOW", created_at=datetime.now(timezone.utc))
        inv = Investigation(id=uuid.uuid4(), alert_id=alt.id, started_at=datetime.now(timezone.utc) + timedelta(minutes=5), duration_seconds=300)
        c = Case(id=uuid.uuid4(), cse_id=cse.id, opened_at=datetime.now(timezone.utc) + timedelta(minutes=10), status="OPEN")

        db.add_all([cse, asset, alt, inv, c])
        db.commit()

        run_id = uuid.uuid4()
        G = SupervisoryEvidenceGraphEngine.build_graph_for_analysis_run(db, run_id)

        path_info = SupervisoryEvidenceGraphEngine.reconstruct_alert_path(G, alt.id)

        # LOW severity alert does NOT mandate Escalation -> Should NOT be anomalous
        assert path_info["severity"] == "LOW"
        assert path_info["is_anomalous"] is False
        assert len(path_info["missing_transitions"]) == 0
    finally:
        db.close()


def test_graph_api_endpoints():
    """Test API endpoints: GET /api/v1/graph/summary/{id}, GET /api/v1/graph/path/{id}, GET /api/v1/graph/anomalies/{id}."""
    client = TestClient(fastapi_app)
    db: Session = SessionLocal()
    try:
        clear_db(db)

        cse = CSE(id=uuid.uuid4(), name="Grid API", sector="ENERGY", entity_type="CRITICAL_INFRASTRUCTURE", size_tier="TIER_1")
        asset = Asset(id=uuid.uuid4(), cse_id=cse.id, name="SCADA Node 1", asset_type="CONTROL_SYSTEM", criticality=AssetCriticality.CRITICAL, status="ACTIVE")
        alt = Alert(id=uuid.uuid4(), cse_id=cse.id, asset_id=asset.id, source_system="SIEM", category="DOS", severity=AlertSeverity.CRITICAL, raw_severity="CRITICAL", created_at=datetime.now(timezone.utc))

        db.add_all([cse, asset, alt])
        db.commit()

        ds = DatasetImport(
            id=uuid.uuid4(),
            filename="test.csv",
            source="CSV_UPLOAD",
            imported_by="test_examiner"
        )
        db.add(ds)
        db.commit()

        run = AnalysisRun(id=uuid.uuid4(), dataset_import_id=ds.id, status="COMPLETED", started_at=datetime.now(timezone.utc))
        db.add(run)
        db.commit()

        # 1. Test Summary Endpoint
        res1 = client.get(f"/api/v1/graph/summary/{run.id}")
        assert res1.status_code == 200
        data1 = res1.json()
        assert "nodes" in data1
        assert "edges" in data1
        assert "metrics" in data1

        # 2. Test Path Reconstruction Endpoint
        res2 = client.get(f"/api/v1/graph/path/{alt.id}")
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["alert_id"] == str(alt.id)
        assert "expected_path" in data2

        # 3. Test Anomalies Endpoint
        res3 = client.get(f"/api/v1/graph/anomalies/{run.id}")
        assert res3.status_code == 200
        data3 = res3.json()
        assert isinstance(data3, list)
    finally:
        db.close()


def test_graph_performance_benchmark():
    """Benchmark SupervisoryEvidenceGraphEngine throughput and metrics over synthetic dataset."""
    config = GeneratorConfig(seed=123, num_cses=5, total_alerts=500)
    generator = SyntheticDatasetGenerator(config)
    dataset = generator.generate()

    with tempfile.TemporaryDirectory() as tmpdir:
        export_dataset_to_csv(dataset, tmpdir)

        db: Session = SessionLocal()
        try:
            clear_db(db)
            pipeline = IngestionPipeline(db=db, imported_by="benchmark_examiner")

            for fn in ["cses.csv", "assets.csv", "analysts.csv", "alerts.csv", "maintenance_logs.csv"]:
                p = os.path.join(tmpdir, fn)
                if os.path.exists(p):
                    pipeline.process_file(p)

            run_id = uuid.uuid4()

            t0 = time.time()
            G = SupervisoryEvidenceGraphEngine.build_graph_for_analysis_run(db, run_id)
            t_build = time.time() - t0

            t1 = time.time()
            anomalies = SupervisoryEvidenceGraphEngine.detect_graph_anomalies(db, G, run_id)
            t_anom = time.time() - t1

            t_total = t_build + t_anom
            metrics = SupervisoryEvidenceGraphEngine.calculate_graph_metrics(G)

            rec_count = metrics["node_count"] + metrics["edge_count"]
            throughput = round(rec_count / t_total, 2) if t_total > 0 else 0.0

            assert metrics["node_count"] > 0
            assert metrics["edge_count"] > 0

            print(f"\n--- PHASE 10 GRAPH BENCHMARK RESULTS ---")
            print(f"Nodes Generated: {metrics['node_count']}")
            print(f"Edges Generated: {metrics['edge_count']}")
            print(f"Anomalies Detected: {len(anomalies)}")
            print(f"Processing Time: {t_total:.4f}s (Build: {t_build:.4f}s, Detect: {t_anom:.4f}s)")
            print(f"Throughput: {throughput} elements/sec")
        finally:
            db.close()
