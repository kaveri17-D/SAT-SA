import uuid
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from pydantic import BaseModel

from app.core.database import get_db
from app.models import ReviewQueueItem, AuditLog, QueueItemStatus, AnalysisRun
from app.analytics.prioritization_engine import ReviewPrioritizationEngine

from app.models import ReviewQueueItem, AuditLog, QueueItemStatus, AnalysisRun, CSE, Finding, Asset, RiskScore, Case, FindingSeverity

router = APIRouter()


class StatusUpdateRequest(BaseModel):
    status: str
    user_id: str = "EXAMINER_01"
    notes: str = ""


@router.get("/metrics/latest", summary="Retrieve Executive Dashboard Overview Metrics")
def get_dashboard_metrics(db: Session = Depends(get_db)):
    """Calculate executive dashboard metrics dynamically across canonical database records."""
    total_cses = db.query(CSE).count()
    risk_scores = db.query(RiskScore).all()
    critical_cses = len([r for r in risk_scores if r.risk_band in ("CRITICAL", "HIGH") or r.normalized_score >= 50.0])

    total_findings = db.query(Finding).count()
    critical_findings = db.query(Finding).filter(Finding.severity == FindingSeverity.CRITICAL).count()

    findings = db.query(Finding).all()
    avg_completeness = round(sum(f.evidence_completeness for f in findings) / len(findings), 1) if findings else 100.0

    open_cases = db.query(Case).filter(Case.status == "OPEN").count()

    queue_items = db.query(ReviewQueueItem).all()
    high_priority_reviews = len([q for q in queue_items if q.priority_score >= 50.0 or q.priority_band in ("CRITICAL", "HIGH")])

    return {
        "total_cses": total_cses,
        "critical_cses": critical_cses,
        "total_findings": total_findings,
        "critical_findings": critical_findings,
        "avg_evidence_completeness": avg_completeness,
        "high_priority_reviews": high_priority_reviews,
        "open_cases": open_cases,
        "airgap_status": "OFFLINE_ACTIVE"
    }


@router.get("/cses", summary="Retrieve All CSE Profiles & Risk Summary")
def get_cse_profiles(db: Session = Depends(get_db)):
    """Retrieve list of all CSEs with risk score, priority band, and asset/finding breakdown."""
    cses = db.query(CSE).all()
    result = []
    for c in cses:
        rs = db.query(RiskScore).filter(RiskScore.cse_id == c.id).first()
        f_count = db.query(Finding).filter(Finding.cse_id == c.id).count()
        a_count = db.query(Asset).filter(Asset.cse_id == c.id).count()

        result.append({
            "cse_id": str(c.id),
            "name": c.name,
            "sector": c.sector,
            "entity_type": c.entity_type,
            "size_tier": c.size_tier,
            "asset_count": a_count,
            "finding_count": f_count,
            "risk_score": rs.normalized_score if rs else 0.0,
            "risk_band": rs.risk_band if rs else "LOW"
        })
    return result


@router.get("/queue/{analysis_run_id}", summary="Retrieve Ranked Supervisory Review Queue")
def get_review_queue(
    analysis_run_id: str,
    max_per_cse: int = Query(2, ge=1, le=10),
    max_per_category: int = Query(3, ge=1, le=10),
    target_queue_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Retrieve or generate ranked supervisory review queue with diversity statistics."""
    if analysis_run_id.lower() == "latest":
        run = db.query(AnalysisRun).order_by(AnalysisRun.created_at.desc()).first()
        if not run:
            # Create a default analysis run for the active dataset
            run = AnalysisRun(id=uuid.uuid4(), status="COMPLETED")
            db.add(run)
            db.commit()
        run_uuid = run.id
    else:
        try:
            run_uuid = uuid.UUID(analysis_run_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid analysis_run_id UUID format."
            )
        run = db.query(AnalysisRun).filter(AnalysisRun.id == run_uuid).first()
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"AnalysisRun '{analysis_run_id}' not found."
            )

    items = db.query(ReviewQueueItem).filter(ReviewQueueItem.analysis_run_id == run_uuid).order_by(ReviewQueueItem.rank.asc()).all()

    if not items:
        # Generate queue dynamically
        items, metrics = ReviewPrioritizationEngine.generate_review_queue(
            db, run_uuid, max_per_cse=max_per_cse, max_per_category=max_per_category, target_queue_size=target_queue_size
        )
    else:
        metrics = {"status": "retrieved_from_cache", "queue_items_count": len(items)}

    return {
        "analysis_run_id": str(run_uuid),
        "queue_count": len(items),
        "metrics": metrics,
        "queue": [
            {
                "queue_item_id": str(item.id),
                "rank": item.rank,
                "priority_score": item.priority_score,
                "priority_band": item.priority_band,
                "finding_id": str(item.finding_id),
                "cse_id": str(item.cse_id),
                "status": item.status.value if item.status else "NEW",
                "rationale": item.rationale,
                "contributing_factors": item.contributing_factors,
                "explanation": item.explanation_json,
                "diversity_notes": item.diversity_notes,
                "provenance": item.provenance_json
            }
            for item in items
        ]
    }


@router.get("/item/{queue_item_id}", summary="Retrieve Queue Item Details & Audit History")
def get_queue_item_detail(queue_item_id: str, db: Session = Depends(get_db)):
    """Retrieve detailed queue item information, explanation, and complete audit history."""
    try:
        item_uuid = uuid.UUID(queue_item_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid queue_item_id UUID format."
        )

    item = db.query(ReviewQueueItem).filter(ReviewQueueItem.id == item_uuid).first()
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ReviewQueueItem '{queue_item_id}' not found."
        )

    audit_logs = db.query(AuditLog).filter(
        AuditLog.entity_type == "ReviewQueueItem",
        AuditLog.entity_id == str(item_uuid)
    ).order_by(AuditLog.timestamp.asc()).all()

    return {
        "queue_item_id": str(item.id),
        "analysis_run_id": str(item.analysis_run_id),
        "finding_id": str(item.finding_id),
        "cse_id": str(item.cse_id),
        "rank": item.rank,
        "priority_score": item.priority_score,
        "priority_band": item.priority_band,
        "status": item.status.value if item.status else "NEW",
        "rationale": item.rationale,
        "contributing_factors": item.contributing_factors,
        "explanation": item.explanation_json,
        "diversity_notes": item.diversity_notes,
        "provenance": item.provenance_json,
        "audit_history": [
            {
                "audit_id": str(a.id),
                "user_id": a.user_id,
                "action": a.action,
                "timestamp": a.timestamp.isoformat(),
                "details": a.before_after_json
            }
            for a in audit_logs
        ]
    }


@router.post("/item/{queue_item_id}/status", summary="Update Review Queue Item Status with Audit Logging")
def update_queue_item_status(queue_item_id: str, payload: StatusUpdateRequest, db: Session = Depends(get_db)):
    """Update queue item status (e.g. IN_REVIEW, ESCALATED, RESOLVED) and record immutable AuditLog entry."""
    try:
        item_uuid = uuid.UUID(queue_item_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid queue_item_id UUID format."
        )

    try:
        new_status_enum = QueueItemStatus(payload.status.upper())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{payload.status}'. Allowed values: {[s.value for s in QueueItemStatus]}."
        )

    try:
        updated_item, audit_log = ReviewPrioritizationEngine.update_item_status(
            db, item_uuid, new_status_enum, user_id=payload.user_id, notes=payload.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

    return {
        "message": f"ReviewQueueItem status updated to '{updated_item.status.value}'.",
        "queue_item_id": str(updated_item.id),
        "status": updated_item.status.value,
        "audit_log_id": str(audit_log.id),
        "updated_at": audit_log.timestamp.isoformat()
    }
