import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.evidence.assembler import EvidenceAssembler

router = APIRouter()


@router.get("/{finding_id}", summary="Retrieve Canonical Evidence Package for Finding")
def get_evidence_package(finding_id: str, db: Session = Depends(get_db)):
    """Retrieve structured, reproducible evidence package for a confirmed finding."""
    try:
        f_uuid = uuid.UUID(finding_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid finding_id UUID format."
        )

    package = EvidenceAssembler.build_evidence_package(db, f_uuid)
    if not package:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Evidence package for finding_id '{finding_id}' not found."
        )

    return package.to_dict()


@router.get("/{finding_id}/verify", summary="Verify Evidence Immutability & Tamper Integrity")
def verify_evidence_integrity(finding_id: str, db: Session = Depends(get_db)):
    """Verify evidence snapshot integrity against underlying canonical database records."""
    try:
        f_uuid = uuid.UUID(finding_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid finding_id UUID format."
        )

    res = EvidenceAssembler.verify_evidence_integrity(db, f_uuid)
    if res.get("status") == "FINDING_NOT_FOUND":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Finding '{finding_id}' not found for verification."
        )

    return res
