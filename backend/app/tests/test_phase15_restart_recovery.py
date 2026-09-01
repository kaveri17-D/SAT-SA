"""Phase 15: Server Restart Recovery and Persistence Validation."""
import os
import tempfile
import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
import app.models
from app.models import AnalysisRun, DatasetImport, ReportType
from app.reporting.builder import ReportBuilder
from app.reporting.schemas import ReportGenerateRequest
from app.reporting.snapshot import SnapshotManager
from app.audit.service import AuditService


def test_restart_recovery_and_persistence():
    """Verify that reports, snapshots, checksums, and audit logs persist and remain valid across DB disconnect/reconnect."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        engine1 = create_engine(f"sqlite:///{tmp_path}", connect_args={"check_same_thread": False})
        Base.metadata.create_all(bind=engine1)
        Session1 = sessionmaker(bind=engine1)
        db1 = Session1()

        # Create assessment & report
        ds = DatasetImport(filename="persist.json", source="P", imported_by="U")
        db1.add(ds)
        db1.flush()
        run = AnalysisRun(dataset_import_id=ds.id)
        db1.add(run)
        db1.commit()

        req = ReportGenerateRequest(assessment_id=str(run.id), report_type=ReportType.EXECUTIVE, title="Persistent Report")
        snap = ReportBuilder.generate_report(db1, req)
        snap_id = snap.id
        stored_checksum = snap.sha256_checksum

        db1.close()
        engine1.dispose()

        # RESTART: Connect with fresh engine & session
        engine2 = create_engine(f"sqlite:///{tmp_path}", connect_args={"check_same_thread": False})
        Session2 = sessionmaker(bind=engine2)
        db2 = Session2()
        try:
            reloaded = db2.query(app.models.ReportSnapshot).filter(app.models.ReportSnapshot.id == snap_id).first()
            assert reloaded is not None
            assert reloaded.sha256_checksum == stored_checksum

            # Verify integrity
            is_valid, msg = SnapshotManager.verify_integrity(reloaded)
            assert is_valid is True

            # Verify audit trail integrity on reloaded DB
            is_audit_valid, total, verified, tampered_id, audit_msg = AuditService.verify_audit_trail_integrity(db2)
            assert is_audit_valid is True
            assert verified >= 1
        finally:
            db2.close()
            engine2.dispose()
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
