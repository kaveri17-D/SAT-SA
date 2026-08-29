import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any

from app.core.database import get_db
from app.models import RiskScore, CSE, AnalysisRun

router = APIRouter()


@router.get("/cse/{cse_id}", summary="Retrieve Supervisory Risk Score & Structured Explanation for CSE")
def get_cse_risk_score(cse_id: str, db: Session = Depends(get_db)):
    """Retrieve latest decomposable supervisory risk score and explanation for a CSE."""
    try:
        c_uuid = uuid.UUID(cse_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid cse_id UUID format."
        )

    risk_record = db.query(RiskScore).filter(RiskScore.cse_id == c_uuid).order_by(RiskScore.computed_at.desc()).first()
    if not risk_record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Supervisory Risk Score found for CSE '{cse_id}'."
        )

    return {
        "risk_score_id": str(risk_record.id),
        "cse_id": str(risk_record.cse_id),
        "analysis_run_id": str(risk_record.analysis_run_id),
        "raw_score": risk_record.raw_score,
        "normalized_score": risk_record.normalized_score,
        "risk_band": risk_record.risk_band,
        "overall_confidence": risk_record.overall_confidence,
        "component_breakdown": risk_record.component_breakdown,
        "contributing_finding_ids": risk_record.contributing_finding_ids or [],
        "explanation": risk_record.explanation_json or {},
        "provenance": risk_record.provenance_json or {},
        "computed_at": risk_record.computed_at.isoformat()
    }


@router.get("/run/{analysis_run_id}", summary="Retrieve All CSE Risk Scores for Analysis Run")
def get_analysis_run_risk_scores(analysis_run_id: str, db: Session = Depends(get_db)):
    """Retrieve all computed CSE risk scores for a given analysis run."""
    try:
        run_uuid = uuid.UUID(analysis_run_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid analysis_run_id UUID format."
        )

    scores = db.query(RiskScore).filter(RiskScore.analysis_run_id == run_uuid).all()
    return [
        {
            "risk_score_id": str(s.id),
            "cse_id": str(s.cse_id),
            "analysis_run_id": str(s.analysis_run_id),
            "raw_score": s.raw_score,
            "normalized_score": s.normalized_score,
            "risk_band": s.risk_band,
            "overall_confidence": s.overall_confidence,
            "component_breakdown": s.component_breakdown,
            "contributing_finding_ids": s.contributing_finding_ids or [],
            "explanation": s.explanation_json or {},
            "computed_at": s.computed_at.isoformat()
        }
        for s in scores
    ]
