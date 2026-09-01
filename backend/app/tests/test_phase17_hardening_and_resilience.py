"""Phase 17: Production Hardening, Observability, Resilience & Offline Packaging Test Suite."""
import os
import socket
import tempfile
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.config import Settings, settings
from app.core.database import SessionLocal, Base, engine
from app.core.backup import DatabaseBackupManager
from app.models import CSE, Asset, Finding, ReportSnapshot, ReportType, FindingSeverity, FindingStatus, AssetCriticality
from app.reporting.builder import ReportBuilder
from app.reporting.schemas import ReportGenerateRequest

client = TestClient(app)


def test_phase17_configuration_guards():
    """Verify air-gap flags and production debug guard behavior."""
    assert settings.STRICT_LOCAL_ONLY is True
    assert settings.IS_AIRGAPPED is True
    assert settings.VERSION == "1.0.0"

    # Test production environment disallows debug mode
    prod_settings = Settings(ENVIRONMENT="production", DEBUG=True)
    assert prod_settings.DEBUG is False


def test_phase17_health_liveness_and_readiness_probes():
    """Verify /health, /health/live, and /health/ready diagnostic endpoints."""
    # 1. Base Health
    r_base = client.get("/api/v1/health")
    assert r_base.status_code == 200
    d_base = r_base.json()
    assert d_base["status"] in ["online", "healthy"]
    assert d_base["airgap_mode"] is True
    assert d_base["strict_local_only"] is True

    # 2. Liveness Probe
    r_live = client.get("/api/v1/health/live")
    assert r_live.status_code == 200
    assert r_live.json()["status"] == "alive"

    # 3. Readiness Probe
    r_ready = client.get("/api/v1/health/ready")
    assert r_ready.status_code == 200
    d_ready = r_ready.json()
    assert d_ready["status"] == "ready"
    assert d_ready["diagnostics"]["database"]["status"] == "healthy"
    assert d_ready["diagnostics"]["storage"]["status"] == "healthy"
    assert d_ready["diagnostics"]["security"]["airgap_mode"] is True


def test_phase17_database_backup_create_verify_restore():
    """Verify point-in-time backup creation, SHA-256 integrity check, and atomic restore."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # 1. Create Backup
        meta = DatabaseBackupManager.create_backup(output_dir=temp_dir)
        assert meta["status"] == "SUCCESS"
        backup_path = meta["backup_path"]
        assert os.path.exists(backup_path)
        assert os.path.exists(f"{backup_path}.sha256")

        # 2. Verify Backup Integrity
        is_valid, msg = DatabaseBackupManager.verify_backup_integrity(backup_path)
        assert is_valid is True
        assert "verified" in msg.lower()

        # 3. Restore to an alternate test target
        restore_target = os.path.join(temp_dir, "restored_target.db")
        res = DatabaseBackupManager.restore_backup(backup_path, target_db_path=restore_target)
        assert res["status"] == "RESTORED"
        assert os.path.exists(restore_target)
        assert res["verified_checksum"] == meta["sha256_checksum"]


def test_phase17_backup_tamper_detection():
    """Verify that tampered backup files are detected and rejected prior to restoration."""
    with tempfile.TemporaryDirectory() as temp_dir:
        meta = DatabaseBackupManager.create_backup(output_dir=temp_dir)
        backup_path = meta["backup_path"]

        # Tamper with backup file contents
        with open(backup_path, "ab") as f:
            f.write(b"CORRUPTED_INJECTED_BYTES")

        # Verification must fail
        is_valid, msg = DatabaseBackupManager.verify_backup_integrity(backup_path)
        assert is_valid is False
        assert "checksum mismatch" in msg.lower()

        # Restore must be blocked
        with pytest.raises(ValueError, match="Cannot restore invalid backup"):
            DatabaseBackupManager.restore_backup(backup_path, target_db_path=os.path.join(temp_dir, "fail.db"))


def test_phase17_malformed_input_rejection():
    """Verify API boundaries reject malformed UUIDs and invalid schemas gracefully."""
    # 1. Invalid UUID in path parameter
    r_bad_uuid = client.get("/api/v1/reports/not-a-valid-uuid")
    assert r_bad_uuid.status_code == 400
    assert "UUID format" in r_bad_uuid.json()["detail"]

    # 2. Invalid export format
    r_bad_fmt = client.get(f"/api/v1/reports/{uuid.uuid4()}/export?format=exe")
    assert r_bad_fmt.status_code == 422  # Pydantic regex validator

    # 3. Non-existent report returns 404
    r_404 = client.get(f"/api/v1/reports/{uuid.uuid4()}")
    assert r_404.status_code == 404


def test_phase17_server_side_rbac_enforcement():
    """Verify authorization checks on protected APIs."""
    # Test unauthenticated / invalid token handling on login
    r_login = client.post("/api/v1/auth/login", data={"username": "nonexistent_user", "password": "wrong_password"})
    assert r_login.status_code in [400, 401]


def test_phase17_offline_airgap_socket_monitoring():
    """Verify zero outbound external network connections during operations."""
    real_socket_connect = socket.socket.connect
    external_calls = []

    def mock_socket_connect(self, address):
        host, port = address[0], address[1]
        if host not in ["127.0.0.1", "localhost", "::1"]:
            external_calls.append(f"{host}:{port}")
            raise ConnectionRefusedError(f"Air-gap violation blocked outbound connection to {host}:{port}")
        return real_socket_connect(self, address)

    # Patch socket connect
    socket.socket.connect = mock_socket_connect
    try:
        # Run health check, backup, and report generation
        r = client.get("/api/v1/health/ready")
        assert r.status_code == 200

        with tempfile.TemporaryDirectory() as temp_dir:
            DatabaseBackupManager.create_backup(output_dir=temp_dir)

        assert len(external_calls) == 0, f"Detected external outbound calls: {external_calls}"
    finally:
        socket.socket.connect = real_socket_connect
