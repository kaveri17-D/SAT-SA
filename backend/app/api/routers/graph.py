import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional

from app.core.database import get_db
from app.models import AnalysisRun, Alert, AnalysisRunStatus
from app.analytics.graph_engine import SupervisoryEvidenceGraphEngine

router = APIRouter(prefix="/graph", tags=["Supervisory Evidence Graph"])


def _resolve_run_uuid(db: Session, analysis_run_id: str) -> uuid.UUID:
    if analysis_run_id.lower() == "latest":
        run = (
            db.query(AnalysisRun)
            .filter(AnalysisRun.status == AnalysisRunStatus.COMPLETED, AnalysisRun.findings_generated > 0)
            .order_by(AnalysisRun.created_at.desc())
            .first()
        )
        if not run:
            run = db.query(AnalysisRun).order_by(AnalysisRun.created_at.desc()).first()
        return run.id if run else uuid.uuid4()
    try:
        return uuid.UUID(analysis_run_id)
    except ValueError:
        return uuid.uuid4()


@router.get("/simple/{analysis_run_id}", summary="Get Scoped Linear Evidence Workflow Path")
def get_simple_workflow(
    analysis_run_id: str,
    cse_id: Optional[str] = None,
    finding_id: Optional[str] = None,
    alert_id: Optional[str] = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Retrieve scoped linear workflow (CSE -> Asset -> Alert -> Investigation -> Escalation -> Case -> Closure) for Simple View."""
    run_uuid = _resolve_run_uuid(db, analysis_run_id)

    cse_uuid = uuid.UUID(cse_id) if cse_id and cse_id.strip() else None
    finding_uuid = uuid.UUID(finding_id) if finding_id and finding_id.strip() else None
    alert_uuid = uuid.UUID(alert_id) if alert_id and alert_id.strip() else None

    return SupervisoryEvidenceGraphEngine.build_simple_workflow_path(
        db=db,
        analysis_run_id=run_uuid,
        cse_id=cse_uuid,
        finding_id=finding_uuid,
        alert_id=alert_uuid
    )


@router.get("/summary/{analysis_run_id}", summary="Get Global Graph Summary & Metrics")
def get_graph_summary(
    analysis_run_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get machine-readable graph JSON representation, nodes, edges, and metrics for an AnalysisRun."""
    run_uuid = _resolve_run_uuid(db, analysis_run_id)
    G = SupervisoryEvidenceGraphEngine.build_graph_for_analysis_run(db, run_uuid, alert_limit=2000)
    return SupervisoryEvidenceGraphEngine.export_graph_json(G, max_nodes=250)


@router.get("/full/{analysis_run_id}", summary="Get Full Evidence Graph (Opt-in)")
def get_full_graph(
    analysis_run_id: str,
    max_nodes: int = Query(1000, ge=50, le=10000),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get full NetworkX evidence graph representation with higher node threshold upon explicit user opt-in."""
    run_uuid = _resolve_run_uuid(db, analysis_run_id)
    G = SupervisoryEvidenceGraphEngine.build_graph_for_analysis_run(db, run_uuid, alert_limit=5000)
    return SupervisoryEvidenceGraphEngine.export_graph_json(G, max_nodes=max_nodes)


@router.get("/path/{alert_id}")
def get_reconstructed_alert_path(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Reconstruct expected vs observed workflow path for a target Alert."""
    alt = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alt:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")

    G = SupervisoryEvidenceGraphEngine.build_graph_for_analysis_run(db, uuid.uuid4(), alert_limit=1000)
    path_info = SupervisoryEvidenceGraphEngine.reconstruct_alert_path(G, alert_id)
    valid_temp, temp_violations = SupervisoryEvidenceGraphEngine.validate_temporal_sequence(G, alert_id)

    path_info["temporal_sequence_valid"] = valid_temp
    path_info["temporal_violations"] = temp_violations
    return path_info


@router.get("/anomalies/{analysis_run_id}")
def get_graph_anomalies(
    analysis_run_id: str,
    db: Session = Depends(get_db)
) -> List[Dict[str, Any]]:
    """Retrieve all detected graph anomalies for an AnalysisRun."""
    run_uuid = _resolve_run_uuid(db, analysis_run_id)
    G = SupervisoryEvidenceGraphEngine.build_graph_for_analysis_run(db, run_uuid, alert_limit=2000)
    return SupervisoryEvidenceGraphEngine.detect_graph_anomalies(db, G, run_uuid)
