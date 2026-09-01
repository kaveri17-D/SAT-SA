"""End-to-End API Integration Tests for Reporting and Audit Routers."""
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
def assessment_setup(db: Session):
    ds = DatasetImport(filename="api_test.json", source="API_TEST", imported_by="TESTER")
    db.add(ds)
    db.flush()
    run = AnalysisRun(dataset_import_id=ds.id)
    db.add(run)
    cse = CSE(name=f"API_CSE_{uuid.uuid4().hex[:6]}", sector="FINANCE", entity_type="BANK", size_tier="TIER_1")
    db.add(cse)
    db.commit()
    return {"run_id": str(run.id), "cse_id": str(cse.id)}


def test_api_generate_and_get_report(client: TestClient, assessment_setup):
    run_id = assessment_setup["run_id"]
    cse_id = assessment_setup["cse_id"]

    # 1. Generate Report
    gen_payload = {
        "assessment_id": run_id,
        "report_type": "EXECUTIVE",
        "cse_id": cse_id,
        "title": "API Test Executive Report",
        "generated_by": "API_EXAMINER"
    }
    resp = client.post("/api/v1/reports/generate", json=gen_payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["report_type"] == "EXECUTIVE"
    report_id = data["id"]

    # 2. List Reports
    list_resp = client.get("/api/v1/reports")
    assert list_resp.status_code == 200
    list_data = list_resp.json()
    assert list_data["total_count"] >= 1
    assert any(r["id"] == report_id for r in list_data["reports"])

    # 3. Get Report Detail
    detail_resp = client.get(f"/api/v1/reports/{report_id}")
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert detail["title"] == "API Test Executive Report"
    assert detail["tamper_verified"] is True

    # 4. Export JSON
    export_json = client.get(f"/api/v1/reports/{report_id}/export?format=json")
    assert export_json.status_code == 200
    assert "report_number" in export_json.json()

    # 5. Export HTML
    export_html = client.get(f"/api/v1/reports/{report_id}/export?format=html")
    assert export_html.status_code == 200
    assert "<!DOCTYPE html>" in export_html.text

    # 6. Evidence Endpoint
    ev_resp = client.get(f"/api/v1/reports/{report_id}/evidence")
    assert ev_resp.status_code == 200
    assert "evidence_references" in ev_resp.json()


def test_api_audit_query_and_verification(client: TestClient):
    # 1. Record event via API
    evt_payload = {
        "user_id": "API_AUDIT_USER",
        "action": "API_AUDIT_ACTION",
        "entity_type": "TEST_ENTITY",
        "entity_id": "ENT-999",
        "actor_role": "ADMIN"
    }
    rec_resp = client.post("/api/v1/audit/events", json=evt_payload)
    assert rec_resp.status_code == 200
    evt_id = rec_resp.json()["id"]

    # 2. Query logs
    q_resp = client.get("/api/v1/audit/logs?user_id=API_AUDIT_USER")
    assert q_resp.status_code == 200
    logs = q_resp.json()["logs"]
    assert any(l["id"] == evt_id for l in logs)

    # 3. Verify audit trail integrity
    v_resp = client.get("/api/v1/audit/verify")
    assert v_resp.status_code == 200
    assert "is_valid" in v_resp.json()
