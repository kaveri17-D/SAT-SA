"""Phase 15: Comprehensive API Integration & Error Handling Validation."""
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from app.main import app
from app.models import DatasetImport, AnalysisRun, CSE, ReportType


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def run_and_cse(db: Session):
    ds = DatasetImport(filename="api_int.json", source="API_INT", imported_by="U")
    db.add(ds)
    db.flush()
    run = AnalysisRun(dataset_import_id=ds.id)
    db.add(run)
    cse = CSE(name=f"API_CSE_{uuid.uuid4().hex[:6]}", sector="GOVERNMENT", entity_type="MINISTRY", size_tier="TIER_1")
    db.add(cse)
    db.commit()
    return {"run_id": str(run.id), "cse_id": str(cse.id)}


def test_api_invalid_uuids_fail_safely(client: TestClient):
    """Verify malformed UUIDs fail safely with 400 Bad Request instead of unhandled 500 exceptions."""
    resp1 = client.get("/api/v1/evidence/finding/not-a-valid-uuid")
    assert resp1.status_code == 400

    resp2 = client.get("/api/v1/risk/cse/invalid-uuid-format")
    assert resp2.status_code == 400

    resp3 = client.get("/api/v1/reports/malformed-id")
    assert resp3.status_code == 400

    resp4 = client.get("/api/v1/audit/logs/not-a-uuid")
    assert resp4.status_code == 400


def test_api_nonexistent_resources_return_404(client: TestClient):
    """Verify nonexistent UUIDs return clean 404 Not Found responses."""
    fake_uuid = "00000000-0000-0000-0000-000000000000"
    resp1 = client.get(f"/api/v1/evidence/finding/{fake_uuid}")
    assert resp1.status_code == 404

    resp2 = client.get(f"/api/v1/risk/cse/{fake_uuid}")
    assert resp2.status_code == 404

    resp3 = client.get(f"/api/v1/reports/{fake_uuid}")
    assert resp3.status_code == 404


def test_api_report_generation_and_export_lifecycle(client: TestClient, run_and_cse):
    """Verify report generation, retrieval, and multi-format export via REST endpoints."""
    run_id = run_and_cse["run_id"]
    cse_id = run_and_cse["cse_id"]

    # Generate Report
    gen_resp = client.post("/api/v1/reports/generate", json={
        "assessment_id": run_id,
        "report_type": "EXECUTIVE",
        "cse_id": cse_id,
        "title": "API Integration Test Report",
        "generated_by": "API_TEST_RUNNER"
    })
    assert gen_resp.status_code == 200
    rep_id = gen_resp.json()["id"]

    # Retrieve Detail
    detail_resp = client.get(f"/api/v1/reports/{rep_id}")
    assert detail_resp.status_code == 200
    assert detail_resp.json()["tamper_verified"] is True

    # Export HTML
    html_resp = client.get(f"/api/v1/reports/{rep_id}/export?format=html")
    assert html_resp.status_code == 200
    assert "text/html" in html_resp.headers.get("content-type", "")

    # Export JSON
    json_resp = client.get(f"/api/v1/reports/{rep_id}/export?format=json")
    assert json_resp.status_code == 200
    assert "application/json" in json_resp.headers.get("content-type", "")
