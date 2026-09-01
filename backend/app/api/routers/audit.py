"""API Router for SAT-SA Cryptographic Audit Trail System."""
import uuid
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import AuditLog
from app.reporting.schemas import AuditEventRequest
from app.audit.service import AuditService

router = APIRouter()


@router.get("/logs", summary="Query and Filter Cryptographic Audit Trail")
def query_audit_logs(
    date_from: Optional[datetime] = Query(None, description="Start timestamp (ISO-8601)"),
    date_to: Optional[datetime] = Query(None, description="End timestamp (ISO-8601)"),
    user_id: Optional[str] = Query(None, description="Filter by user/examiner ID"),
    actor_role: Optional[str] = Query(None, description="Filter by role (EXAMINER, ADMIN, ANALYST)"),
    action: Optional[str] = Query(None, description="Filter by action string"),
    entity_type: Optional[str] = Query(None, description="Filter by resource entity type"),
    entity_id: Optional[str] = Query(None, description="Filter by resource entity ID"),
    status: Optional[str] = Query(None, description="Filter by status (SUCCESS, FAILED, DENIED)"),
    correlation_id: Optional[str] = Query(None, description="Filter by correlation/tracing ID"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    """Query append-only audit trail logs with filtering, sorting, and pagination."""
    logs, total_count = AuditService.query_logs(
        db=db,
        date_from=date_from,
        date_to=date_to,
        user_id=user_id,
        actor_role=actor_role,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        status=status,
        correlation_id=correlation_id,
        limit=limit,
        offset=offset
    )

    items = []
    for l in logs:
        items.append({
            "id": str(l.id),
            "user_id": l.user_id,
            "actor_role": l.actor_role,
            "action": l.action,
            "entity_type": l.entity_type,
            "entity_id": l.entity_id,
            "timestamp": l.timestamp.isoformat(),
            "status": l.status,
            "correlation_id": l.correlation_id,
            "before_after": l.before_after_json,
            "metadata": l.metadata_json,
            "integrity_hash": l.integrity_hash,
            "previous_hash": l.previous_hash
        })

    return {
        "total_count": total_count,
        "page_size": limit,
        "offset": offset,
        "logs": items
    }


@router.get("/logs/{log_id}", summary="Retrieve Specific Audit Log Entry Detail")
def get_audit_log_detail(log_id: str, db: Session = Depends(get_db)):
    """Retrieve full audit log entry details."""
    try:
        l_uuid = uuid.UUID(log_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid log_id UUID format.")

    log_entry = db.query(AuditLog).filter(AuditLog.id == l_uuid).first()
    if not log_entry:
        raise HTTPException(status_code=404, detail=f"Audit log entry '{log_id}' not found.")

    return {
        "id": str(log_entry.id),
        "user_id": log_entry.user_id,
        "actor_role": log_entry.actor_role,
        "action": log_entry.action,
        "entity_type": log_entry.entity_type,
        "entity_id": log_entry.entity_id,
        "timestamp": log_entry.timestamp.isoformat(),
        "status": log_entry.status,
        "correlation_id": log_entry.correlation_id,
        "before_after": log_entry.before_after_json,
        "metadata": log_entry.metadata_json,
        "integrity_hash": log_entry.integrity_hash,
        "previous_hash": log_entry.previous_hash,
        "analysis_run_id": str(log_entry.analysis_run_id) if log_entry.analysis_run_id else None,
        "dataset_import_id": str(log_entry.dataset_import_id) if log_entry.dataset_import_id else None
    }


@router.get("/verify", summary="Verify Entire Cryptographic Audit Trail Integrity")
def verify_audit_trail(db: Session = Depends(get_db)):
    """Verify hash chaining and detect any tampering across the entire audit history."""
    is_valid, total, verified, tampered_id, details = AuditService.verify_audit_trail_integrity(db)
    return {
        "is_valid": is_valid,
        "total_events": total,
        "verified_events": verified,
        "tampered_event_id": tampered_id,
        "details": details
    }


@router.post("/events", summary="Record Cryptographic Audit Event")
def record_audit_event(req: AuditEventRequest, db: Session = Depends(get_db)):
    """Explicitly record an audit event in the cryptographic ledger."""
    entry = AuditService.log_event(
        db=db,
        user_id=req.user_id,
        action=req.action,
        entity_type=req.entity_type,
        entity_id=req.entity_id,
        actor_role=req.actor_role,
        status=req.status,
        correlation_id=req.correlation_id,
        before_after=req.before_after,
        metadata=req.metadata
    )
    return {
        "id": str(entry.id),
        "integrity_hash": entry.integrity_hash,
        "timestamp": entry.timestamp.isoformat(),
        "status": "RECORDED"
    }
