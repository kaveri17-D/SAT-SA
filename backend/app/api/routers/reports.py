"""API Router for SAT-SA Reporting System."""
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session, joinedload

from app.core.database import get_db
from app.models import ReportSnapshot, ReportEvidenceReference, ReportType, ReportStatus
from app.reporting.schemas import ReportGenerateRequest, ReportSummaryDTO, ReportDetailDTO
from app.reporting.builder import ReportBuilder
from app.reporting.snapshot import SnapshotManager
from app.reporting.exporters.json_exporter import JSONReportExporter
from app.reporting.exporters.html_exporter import HTMLReportExporter
from app.audit.service import AuditService

router = APIRouter()


@router.post("/generate", summary="Generate Immutable Assessment Report Snapshot")
def generate_report(request: ReportGenerateRequest, db: Session = Depends(get_db)):
    """Generate a new report snapshot from current assessment state."""
    try:
        snapshot = ReportBuilder.generate_report(db, request)
        return {
            "id": str(snapshot.id),
            "report_number": snapshot.report_number,
            "report_type": snapshot.report_type.value if hasattr(snapshot.report_type, "value") else str(snapshot.report_type),
            "status": snapshot.status.value if hasattr(snapshot.status, "value") else str(snapshot.status),
            "title": snapshot.title,
            "assessment_id": str(snapshot.analysis_run_id),
            "cse_id": str(snapshot.cse_id) if snapshot.cse_id else None,
            "generated_at": snapshot.generated_at.isoformat(),
            "generated_by": snapshot.generated_by,
            "sha256_checksum": snapshot.sha256_checksum,
            "is_tampered": snapshot.is_tampered,
            "summary": snapshot.summary_json
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate report: {str(e)}")


@router.get("", summary="List Generated Report Snapshots")
def list_reports(
    assessment_id: Optional[str] = Query(None, description="Filter by AnalysisRun UUID"),
    cse_id: Optional[str] = Query(None, description="Filter by CSE UUID"),
    report_type: Optional[str] = Query(None, description="Filter by ReportType"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """List historical report snapshots with filtering and pagination."""
    query = db.query(ReportSnapshot).options(joinedload(ReportSnapshot.cse))

    if assessment_id:
        try:
            query = query.filter(ReportSnapshot.analysis_run_id == uuid.UUID(assessment_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid assessment_id UUID format.")

    if cse_id:
        try:
            query = query.filter(ReportSnapshot.cse_id == uuid.UUID(cse_id))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid cse_id UUID format.")

    if report_type:
        query = query.filter(ReportSnapshot.report_type == report_type)

    total_count = query.count()
    snapshots = query.order_by(ReportSnapshot.generated_at.desc()).offset(offset).limit(limit).all()

    items = []
    for s in snapshots:
        items.append({
            "id": str(s.id),
            "report_number": s.report_number,
            "report_type": s.report_type.value if hasattr(s.report_type, "value") else str(s.report_type),
            "status": s.status.value if hasattr(s.status, "value") else str(s.status),
            "title": s.title,
            "assessment_id": str(s.analysis_run_id),
            "cse_id": str(s.cse_id) if s.cse_id else None,
            "cse_name": s.cse.name if s.cse else None,
            "generated_at": s.generated_at.isoformat(),
            "generated_by": s.generated_by,
            "sha256_checksum": s.sha256_checksum,
            "is_tampered": s.is_tampered,
            "summary": s.summary_json
        })

    return {
        "total_count": total_count,
        "page_size": limit,
        "offset": offset,
        "reports": items
    }


@router.get("/{report_id}", summary="Retrieve Report Snapshot Detail & Verify Tamper Integrity")
def get_report_detail(report_id: str, db: Session = Depends(get_db)):
    """Retrieve full report snapshot and recompute cryptographic integrity check."""
    try:
        r_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report_id UUID format.")

    snapshot = db.query(ReportSnapshot).filter(ReportSnapshot.id == r_uuid).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Report snapshot '{report_id}' not found.")

    is_valid, msg = SnapshotManager.verify_integrity(snapshot)
    db.commit()  # save is_tampered if altered

    ev_refs = []
    for ref in snapshot.evidence_refs:
        ev_refs.append({
            "id": str(ref.id),
            "finding_id": str(ref.finding_id) if ref.finding_id else None,
            "evidence_id": str(ref.evidence_id) if ref.evidence_id else None,
            "evidence_type": ref.evidence_type,
            "source_table": ref.source_table,
            "source_record_id": ref.source_record_id,
            "relevance": ref.relevance,
            "description": ref.description,
            "provenance": ref.provenance_json or {}
        })

    return {
        "id": str(snapshot.id),
        "report_number": snapshot.report_number,
        "report_type": snapshot.report_type.value if hasattr(snapshot.report_type, "value") else str(snapshot.report_type),
        "status": snapshot.status.value if hasattr(snapshot.status, "value") else str(snapshot.status),
        "title": snapshot.title,
        "description": snapshot.description,
        "assessment_id": str(snapshot.analysis_run_id),
        "cse_id": str(snapshot.cse_id) if snapshot.cse_id else None,
        "cse_name": snapshot.cse.name if snapshot.cse else None,
        "generated_at": snapshot.generated_at.isoformat(),
        "generated_by": snapshot.generated_by,
        "schema_version": snapshot.schema_version,
        "system_version": snapshot.system_version,
        "data_foundation_version": snapshot.data_foundation_version,
        "sha256_checksum": snapshot.sha256_checksum,
        "is_tampered": snapshot.is_tampered,
        "tamper_verified": is_valid,
        "tamper_message": msg,
        "summary": snapshot.summary_json,
        "content": snapshot.content_json,
        "metadata": snapshot.metadata_json or {},
        "evidence_references": ev_refs
    }


@router.get("/{report_id}/export", summary="Export Report Snapshot as JSON or HTML")
def export_report(
    report_id: str,
    format: str = Query("json", pattern="^(?i)(json|html|pdf)$"),
    db: Session = Depends(get_db)
):
    """Export report snapshot into JSON, HTML, or PDF formats with download headers."""
    try:
        r_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report_id UUID format.")

    snapshot = db.query(ReportSnapshot).options(joinedload(ReportSnapshot.cse)).filter(ReportSnapshot.id == r_uuid).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Report snapshot '{report_id}' not found.")

    fmt = format.lower()
    ext = "html" if fmt in ("html", "pdf") else "json"
    filename = f"{snapshot.report_number}.{ext}"
    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"'
    }

    # Audit event
    AuditService.log_event(
        db=db,
        user_id="EXAMINER_NCIIPC",
        action="REPORT_EXPORTED",
        entity_type="REPORT_SNAPSHOT",
        entity_id=str(snapshot.id),
        metadata={"format": fmt.upper(), "report_number": snapshot.report_number}
    )

    if fmt in ("html", "pdf"):
        html_content = HTMLReportExporter.export(snapshot)
        return Response(content=html_content, media_type="text/html", headers=headers)
    else:
        json_content = JSONReportExporter.export(snapshot)
        return Response(content=json_content, media_type="application/json", headers=headers)


@router.get("/{report_id}/evidence", summary="Retrieve Evidence References Supporting Report")
def get_report_evidence(report_id: str, db: Session = Depends(get_db)):
    """Retrieve full evidence references and provenance linkages for a report."""
    try:
        r_uuid = uuid.UUID(report_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid report_id UUID format.")

    snapshot = db.query(ReportSnapshot).filter(ReportSnapshot.id == r_uuid).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"Report snapshot '{report_id}' not found.")

    ev_refs = []
    for ref in snapshot.evidence_refs:
        ev_refs.append({
            "id": str(ref.id),
            "finding_id": str(ref.finding_id) if ref.finding_id else None,
            "evidence_id": str(ref.evidence_id) if ref.evidence_id else None,
            "evidence_type": ref.evidence_type,
            "source_table": ref.source_table,
            "source_record_id": ref.source_record_id,
            "relevance": ref.relevance,
            "description": ref.description,
            "provenance": ref.provenance_json or {}
        })

    return {
        "report_id": str(snapshot.id),
        "report_number": snapshot.report_number,
        "evidence_count": len(ev_refs),
        "evidence_references": ev_refs
    }
