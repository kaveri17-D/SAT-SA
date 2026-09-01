"""Tests for Report Exporters (JSON and HTML)."""
import json
import pytest
from datetime import datetime, timezone
from app.models import ReportSnapshot, ReportType, ReportStatus
from app.reporting.exporters.json_exporter import JSONReportExporter
from app.reporting.exporters.html_exporter import HTMLReportExporter


@pytest.fixture
def sample_snapshot():
    return ReportSnapshot(
        report_number="REP-20260901-TEST1234",
        report_type=ReportType.EXECUTIVE,
        status=ReportStatus.COMPLETED,
        title="Executive Cyber Assessment Report",
        generated_at=datetime.now(timezone.utc),
        generated_by="EXAMINER_TEST",
        sha256_checksum="a" * 64,
        is_tampered=False,
        summary_json={
            "overall_security_posture": "ELEVATED",
            "overall_risk_score": 62.5,
            "total_findings": 8,
            "critical_findings": 2,
            "kev_exposures_count": 1
        },
        content_json={
            "report_header": {"title": "Executive Cyber Assessment Report"},
            "executive_summary": {"narrative": "Assessment completed with critical findings."}
        },
        metadata_json={"export_scope": "ALL"}
    )


def test_json_exporter(sample_snapshot):
    json_str = JSONReportExporter.export(sample_snapshot)
    assert json_str is not None
    data = json.loads(json_str)
    assert data["report_number"] == "REP-20260901-TEST1234"
    assert data["sha256_checksum"] == "a" * 64
    assert data["summary"]["overall_risk_score"] == 62.5


def test_html_exporter(sample_snapshot):
    html_str = HTMLReportExporter.export(sample_snapshot)
    assert html_str is not None
    assert "<!DOCTYPE html>" in html_str
    assert "Executive Cyber Assessment Report" in html_str
    assert "REP-20260901-TEST1234" in html_str
    assert "62.5" in html_str
    assert "SHA-256 Checksum" in html_str
