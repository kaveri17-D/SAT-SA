"""Phase 15: Real Backend Startup, Configuration, and Lifecycle Validation."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core.database import engine, Base


def test_backend_configuration_loading():
    """Verify production-ready configuration values."""
    assert "SAT-SA" in settings.PROJECT_NAME
    assert settings.API_V1_STR == "/api/v1"
    assert settings.DATABASE_URL is not None


def test_backend_app_instance_and_metadata():
    """Verify FastAPI application instance and metadata."""
    assert app.title == settings.PROJECT_NAME
    assert app.version == "1.0.0"
    assert app.openapi_url == "/api/v1/openapi.json"
    assert app.docs_url == "/api/v1/docs"


def test_backend_routers_registered():
    """Verify all 8 core routers are registered with correct prefixes."""
    paths = app.openapi()["paths"].keys()
    assert "/api/v1/health" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/evidence/finding/{finding_id}" in paths
    assert "/api/v1/risk/cse/{cse_id}" in paths
    assert "/api/v1/prioritization/queue/{analysis_run_id}" in paths
    assert "/api/v1/graph/summary/{analysis_run_id}" in paths
    assert "/api/v1/reports/generate" in paths
    assert "/api/v1/audit/logs" in paths
    assert "/api/v1/audit/verify" in paths


def test_backend_health_endpoint_response():
    """Verify live health endpoint response contract."""
    client = TestClient(app)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "online"
    assert "SAT-SA" in data["service"]
    assert data["airgap_mode"] is True
    assert data["version"] == "1.0.0"
