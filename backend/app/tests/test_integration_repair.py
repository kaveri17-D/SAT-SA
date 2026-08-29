import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy import inspect
from app.main import app
from app.core.database import SessionLocal, engine
from app.models import Base, CSE, Finding, RiskScore, ReviewQueueItem, MaintenanceLog, AnalysisRun
from app.db.bootstrap_demo import bootstrap_demo_dataset

client = TestClient(app)


@pytest.fixture(scope="module")
def setup_bootstrapped_db():
    """Bootstrap complete dataset in test database."""
    run_id = bootstrap_demo_dataset(force_rebuild=True)
    yield run_id


def test_schema_all_22_tables_and_columns(setup_bootstrapped_db):
    """Verify all 22 canonical model tables exist in database schema."""
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    
    expected_tables = {
        "cses", "assets", "alerts", "investigations", "analysts", "escalations",
        "cases", "closures", "maintenance_logs", "dataset_imports", "data_quality_issues", "rule_versions",
        "model_versions", "analysis_runs", "audit_logs", "findings", "evidence",
        "risk_scores", "peer_groups", "peer_group_memberships", "benchmarks", "review_queue_items"
    }
    
    for table in expected_tables:
        assert table in table_names, f"Table '{table}' missing from database schema."
        
    # Check specific columns added in migration
    findings_cols = [c["name"] for c in inspector.get_columns("findings")]
    assert "evidence_completeness" in findings_cols
    
    risk_cols = [c["name"] for c in inspector.get_columns("risk_scores")]
    assert "normalized_score" in risk_cols
    assert "risk_band" in risk_cols
    assert "overall_confidence" in risk_cols
    assert "explanation_json" in risk_cols
    
    evidence_cols = [c["name"] for c in inspector.get_columns("evidence")]
    assert "relevance" in evidence_cols
    assert "payload_json" in evidence_cols
    assert "provenance_json" in evidence_cols


def test_prioritization_cses_endpoint(setup_bootstrapped_db):
    """Verify GET /api/v1/prioritization/cses returns all CSE profiles with valid risk scores."""
    response = client.get("/api/v1/prioritization/cses")
    assert response.status_code == 200
    cses = response.json()
    assert len(cses) > 0
    for c in cses:
        assert "cse_id" in c
        assert "name" in c
        assert "sector" in c
        assert "risk_score" in c
        assert "risk_band" in c
        assert isinstance(c["risk_score"], (int, float))
        assert c["risk_band"] in ("CRITICAL", "HIGH", "MODERATE", "MEDIUM", "LOW")


def test_prioritization_metrics_endpoint(setup_bootstrapped_db):
    """Verify GET /api/v1/prioritization/metrics/latest returns overview metrics."""
    response = client.get("/api/v1/prioritization/metrics/latest")
    assert response.status_code == 200
    metrics = response.json()
    assert "total_cses" in metrics
    assert "critical_cses" in metrics
    assert "total_findings" in metrics
    assert "avg_evidence_completeness" in metrics
    assert metrics["total_cses"] > 0
    assert metrics["total_findings"] > 0


def test_prioritization_queue_and_item_workflow(setup_bootstrapped_db):
    """Verify review queue retrieval, item inspection, and examiner status transition."""
    run_id = setup_bootstrapped_db
    
    # 1. Fetch queue by run_id
    response = client.get(f"/api/v1/prioritization/queue/{run_id}")
    assert response.status_code == 200
    data = response.json()
    assert "queue" in data
    queue = data["queue"]
    assert len(queue) > 0
    
    item = queue[0]
    queue_item_id = item["queue_item_id"]
    finding_id = item["finding_id"]
    cse_id = item["cse_id"]
    
    # 2. Fetch queue by 'latest' alias
    resp_latest = client.get("/api/v1/prioritization/queue/latest")
    assert resp_latest.status_code == 200
    assert len(resp_latest.json()["queue"]) > 0
    
    # 3. Fetch item detail
    resp_item = client.get(f"/api/v1/prioritization/item/{queue_item_id}")
    assert resp_item.status_code == 200
    item_detail = resp_item.json()
    assert item_detail["queue_item_id"] == queue_item_id
    assert "audit_history" in item_detail
    
    # 4. Update item status with audit trail
    status_payload = {"status": "IN_REVIEW", "user_id": "EXAMINER_TEST", "notes": "Auditing evidence package"}
    resp_update = client.post(f"/api/v1/prioritization/item/{queue_item_id}/status", json=status_payload)
    assert resp_update.status_code == 200
    assert resp_update.json()["status"] == "IN_REVIEW"
    
    # 5. Verify audit history recorded
    resp_item2 = client.get(f"/api/v1/prioritization/item/{queue_item_id}")
    assert resp_item2.json()["status"] == "IN_REVIEW"
    assert len(resp_item2.json()["audit_history"]) >= 1


def test_evidence_package_and_alias_route(setup_bootstrapped_db):
    """Verify evidence package retrieval via canonical and alias routes, and tamper integrity."""
    db = SessionLocal()
    try:
        finding = db.query(Finding).first()
        assert finding is not None
        finding_id = str(finding.id)
    finally:
        db.close()
        
    # Canonical route
    resp1 = client.get(f"/api/v1/evidence/{finding_id}")
    assert resp1.status_code == 200
    pkg1 = resp1.json()
    assert pkg1["finding_id"] == finding_id
    assert "supporting_records" in pkg1
    assert "records" in pkg1
    assert len(pkg1["records"]) > 0
    assert "deviation" in pkg1
    
    # Alias route (/finding/{finding_id})
    resp2 = client.get(f"/api/v1/evidence/finding/{finding_id}")
    assert resp2.status_code == 200
    pkg2 = resp2.json()
    assert pkg2["finding_id"] == finding_id
    
    # Tamper verification
    resp_ver = client.get(f"/api/v1/evidence/{finding_id}/verify")
    assert resp_ver.status_code == 200
    assert resp_ver.json()["is_tampered"] is False
    assert resp_ver.json()["evidence_count"] > 0


def test_risk_score_cse_and_contributions(setup_bootstrapped_db):
    """Verify CSE risk score contains both contributions and explanation fields."""
    db = SessionLocal()
    try:
        cse = db.query(CSE).first()
        assert cse is not None
        cse_id = str(cse.id)
    finally:
        db.close()
        
    response = client.get(f"/api/v1/risk/cse/{cse_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["cse_id"] == cse_id
    assert "normalized_score" in data
    assert "contributions" in data
    assert "explanation" in data
    assert isinstance(data["contributions"], list)


def test_graph_summary_and_anomalies(setup_bootstrapped_db):
    """Verify graph endpoints return consistent node/edge data and anomaly list."""
    run_id = setup_bootstrapped_db
    
    resp_sum = client.get(f"/api/v1/graph/summary/{run_id}")
    assert resp_sum.status_code == 200
    summary = resp_sum.json()
    assert "nodes" in summary
    assert "edges" in summary
    assert summary["metrics"]["node_count"] > 0
    
    resp_anom = client.get(f"/api/v1/graph/anomalies/{run_id}")
    assert resp_anom.status_code == 200
    anomalies = resp_anom.json()
    assert isinstance(anomalies, list)


def test_maintenance_logs_persisted(setup_bootstrapped_db):
    """Verify maintenance logs table is populated during synthetic ingestion."""
    db = SessionLocal()
    try:
        count = db.query(MaintenanceLog).count()
        assert count > 0, "Expected at least 1 MaintenanceLog record persisted."
    finally:
        db.close()
