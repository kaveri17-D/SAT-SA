"""Tests for Report Snapshot Creation, SHA-256 Signing, and Tamper Verification."""
import json
import pytest
from sqlalchemy.orm import Session
from app.models import ReportSnapshot, ReportType, ReportStatus
from app.reporting.snapshot import SnapshotManager
from app.reporting.schemas import ReportGenerateRequest
from app.reporting.builder import ReportBuilder


def test_snapshot_creation_and_integrity_verification(db: Session):
    # Generate test snapshot
    from app.models import AnalysisRun, DatasetImport
    ds = DatasetImport(filename="t.json", source="T", imported_by="U")
    db.add(ds)
    db.flush()
    run = AnalysisRun(dataset_import_id=ds.id)
    db.add(run)
    db.commit()

    summary = {"total_findings": 3, "overall_risk_score": 45.0}
    content = {
        "report_header": {"title": "Test Assessment Report"},
        "findings": [{"id": "F1", "severity": "HIGH"}]
    }

    snapshot = SnapshotManager.create_and_sign_snapshot(
        db=db,
        analysis_run_id=str(run.id),
        report_type=ReportType.EXECUTIVE,
        summary=summary,
        content=content,
        evidence_refs=[],
        title="Test Executive Report"
    )

    assert snapshot.id is not None
    assert len(snapshot.sha256_checksum) == 64
    assert snapshot.is_tampered is False

    # Verify authentic integrity
    is_valid, msg = SnapshotManager.verify_integrity(snapshot)
    assert is_valid is True
    assert "Integrity verified" in msg


def test_snapshot_tamper_detection_on_altered_payload(db: Session):
    from app.models import AnalysisRun, DatasetImport
    ds = DatasetImport(filename="t2.json", source="T", imported_by="U")
    db.add(ds)
    db.flush()
    run = AnalysisRun(dataset_import_id=ds.id)
    db.add(run)
    db.commit()

    snapshot = SnapshotManager.create_and_sign_snapshot(
        db=db,
        analysis_run_id=str(run.id),
        report_type=ReportType.TECHNICAL,
        summary={"findings": 1},
        content={"data": "ORIGINAL_AUTHENTIC_DATA"},
        evidence_refs=[],
        title="Authentic Technical Report"
    )

    # Tamper with stored content
    snapshot.content_json = {"data": "MALICIOUSLY_ALTERED_DATA"}
    is_valid, msg = SnapshotManager.verify_integrity(snapshot)
    assert is_valid is False
    assert "Tamper detected" in msg
    assert snapshot.is_tampered is True
