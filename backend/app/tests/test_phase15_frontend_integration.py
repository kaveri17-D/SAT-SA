"""Phase 15: Frontend API Contract & Integration Validation."""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_frontend_dashboard_metrics_contract(client: TestClient):
    """Verify DashboardMetrics response matches frontend TypeScript interface."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "service" in data
    assert "version" in data
    assert "airgap_mode" in data


def test_frontend_reports_list_contract(client: TestClient):
    """Verify Reports list response matches ReportSummary[] TypeScript interface."""
    resp = client.get("/api/v1/reports")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_count" in data
    assert "reports" in data
    assert isinstance(data["reports"], list)


def test_frontend_audit_verify_contract(client: TestClient):
    """Verify Audit verify response matches AuditVerificationResult TypeScript interface."""
    resp = client.get("/api/v1/audit/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert "is_valid" in data
    assert "total_events" in data
    assert "verified_events" in data
    assert "details" in data
