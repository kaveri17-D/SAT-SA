"""Phase 15: Concurrency and Thread-Safe Operations Validation."""
import concurrent.futures
import uuid
import pytest
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models import DatasetImport, AnalysisRun, CSE, ReportType
from app.reporting.builder import ReportBuilder
from app.reporting.schemas import ReportGenerateRequest
from app.audit.service import AuditService


def test_concurrent_report_generation(db: Session):
    """Verify multiple concurrent report generation requests succeed without collision or deadlock."""
    ds = DatasetImport(filename="conc.json", source="CONC", imported_by="U")
    db.add(ds)
    db.flush()
    run = AnalysisRun(dataset_import_id=ds.id)
    db.add(run)
    cse = CSE(name="CONC_CSE", sector="ENERGY", entity_type="GRID", size_tier="TIER_1")
    db.add(cse)
    db.commit()
    run_id = str(run.id)
    cse_id = str(cse.id)

    def generate_single_report(rep_type):
        session = SessionLocal()
        try:
            req = ReportGenerateRequest(
                assessment_id=run_id,
                report_type=rep_type,
                cse_id=cse_id,
                title=f"Concurrent {rep_type.value} Report"
            )
            snapshot = ReportBuilder.generate_report(session, req)
            return snapshot.id, snapshot.report_number
        finally:
            session.close()

    types = [ReportType.EXECUTIVE, ReportType.TECHNICAL, ReportType.RISK, ReportType.ASSET]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(generate_single_report, types))

    assert len(results) == 4
    report_numbers = [r[1] for r in results]
    assert len(set(report_numbers)) == 4  # All report numbers must be unique
