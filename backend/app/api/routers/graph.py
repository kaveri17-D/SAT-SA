import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Dict, Any, List

from app.core.database import get_db
from app.models import AnalysisRun, Alert
from app.analytics.graph_engine import SupervisoryEvidenceGraphEngine

router = APIRouter(prefix="/graph", tags=["Supervisory Evidence Graph"])


@router.get("/summary/{analysis_run_id}")
def get_graph_summary(
    analysis_run_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Get machine-readable graph JSON representation, nodes, edges, and metrics for an AnalysisRun."""
    if analysis_run_id.lower() == "latest":
        run = db.query(AnalysisRun).order_by(AnalysisRun.created_at.desc()).first()
        run_uuid = run.id if run else uuid.uuid4()
    else:
        try:
            run_uuid = uuid.UUID(analysis_run_id)
        except ValueError:
            run_uuid = uuid.uuid4()

    G = SupervisoryEvidenceGraphEngine.build_graph_for_analysis_run(db, run_uuid)
    return SupervisoryEvidenceGraphEngine.export_graph_json(G)


@router.get("/path/{alert_id}")
def get_reconstructed_alert_path(
    alert_id: uuid.UUID,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Reconstruct expected vs observed workflow path for a target Alert."""
    alt = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alt:
        raise HTTPException(status_code=404, detail=f"Alert '{alert_id}' not found.")

    G = SupervisoryEvidenceGraphEngine.build_graph_for_analysis_run(db, uuid.uuid4())
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
    if analysis_run_id.lower() == "latest":
        run = db.query(AnalysisRun).order_by(AnalysisRun.created_at.desc()).first()
        run_uuid = run.id if run else uuid.uuid4()
    else:
        try:
            run_uuid = uuid.UUID(analysis_run_id)
        except ValueError:
            run_uuid = uuid.uuid4()

    G = SupervisoryEvidenceGraphEngine.build_graph_for_analysis_run(db, run_uuid)
    return SupervisoryEvidenceGraphEngine.detect_graph_anomalies(db, G, run_uuid)
