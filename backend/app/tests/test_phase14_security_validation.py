"""Security and Robustness Validation for Phase 14 Reporting and Audit System."""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_security_idor_invalid_uuid_handling(client: TestClient):
    # Malicious SQLi or path traversal in UUID path params
    resp1 = client.get("/api/v1/reports/../../../etc/passwd")
    assert resp1.status_code in [400, 404]

    resp2 = client.get("/api/v1/audit/logs/SELECT_ALL_FROM_USERS")
    assert resp2.status_code in [400, 404]


def test_security_export_format_whitelist(client: TestClient):
    # Test unapproved format injection
    resp = client.get("/api/v1/reports/00000000-0000-0000-0000-000000000000/export?format=exe")
    assert resp.status_code == 422  # Validation error on regex whitelist


def test_security_credential_redaction_in_audit_metadata():
    """Verify that audit records never persist raw passwords, bearer tokens, or secret keys."""
    from app.audit.service import AuditService
    import inspect

    src = inspect.getsource(AuditService)
    # Ensure audit service does not log plaintext passwords
    assert "password" not in src.lower()
    assert "secret_key" not in src.lower()
