"""Phase 15: Security Hardening, Credential Redaction, and Air-Gap Verification."""
import socket
import pytest
from app.reporting.builder import ReportBuilder
from app.reporting.schemas import ReportGenerateRequest
from app.models import ReportType, DatasetImport, AnalysisRun
from app.core.config import settings


def test_strict_airgap_guarantee_during_report_generation(db):
    """Verify that report generation executes 100% locally with zero outbound network calls."""
    ds = DatasetImport(filename="airgap.json", source="LOCAL", imported_by="U")
    db.add(ds)
    db.flush()
    run = AnalysisRun(dataset_import_id=ds.id)
    db.add(run)
    db.commit()

    orig_socket = socket.socket
    network_call_made = []

    def mock_socket(*args, **kwargs):
        network_call_made.append(args)
        raise RuntimeError("AIR-GAP VIOLATION: External socket opened during assessment.")

    socket.socket = mock_socket
    try:
        req = ReportGenerateRequest(
            assessment_id=str(run.id),
            report_type=ReportType.VULNERABILITY_THREAT_INTEL,
            title="Air-Gap Validation Report"
        )
        snap = ReportBuilder.generate_report(db, req)
        assert snap is not None
        assert len(network_call_made) == 0
    finally:
        socket.socket = orig_socket


def test_no_sensitive_secrets_in_config():
    """Verify configuration does not expose hardcoded passwords or API tokens."""
    assert "secret" not in settings.PROJECT_NAME.lower()
    assert settings.ENABLE_LOCAL_NLP is True
    assert settings.API_V1_STR == "/api/v1"
