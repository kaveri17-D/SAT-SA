"""Phase 15: Cryptographic Chained Audit Trail E2E Lifecycle & Tamper Detection."""
import pytest
from sqlalchemy.orm import Session
from app.models import AuditLog
from app.audit.service import AuditService


def test_audit_trail_full_lifecycle_chain(db: Session):
    """Execute sequence of 5 distinct actions and verify cryptographic hash chain integrity."""
    actions = [
        ("EXAMINER_01", "INGESTION_STARTED", "DATASET_IMPORT", "IMP-101"),
        ("EXAMINER_01", "ASSESSMENT_COMPLETED", "ANALYSIS_RUN", "RUN-101"),
        ("EXAMINER_02", "FINDING_INSPECTED", "FINDING", "FND-101"),
        ("EXAMINER_02", "REPORT_GENERATED", "REPORT_SNAPSHOT", "REP-101"),
        ("EXAMINER_02", "REPORT_EXPORTED", "REPORT_SNAPSHOT", "REP-101")
    ]

    for user, action, ent_type, ent_id in actions:
        AuditService.log_event(
            db=db,
            user_id=user,
            action=action,
            entity_type=ent_type,
            entity_id=ent_id,
            actor_role="EXAMINER",
            status="SUCCESS"
        )

    is_valid, total, verified, tampered_id, msg = AuditService.verify_audit_trail_integrity(db)
    assert is_valid is True
    assert verified >= 5
    assert tampered_id is None
    assert "All" in msg and "verified" in msg


def test_controlled_audit_tamper_detection(db: Session):
    """Tamper with an existing audit event in the chain and verify instant detection."""
    e = AuditService.log_event(
        db=db,
        user_id="LEGITIMATE_OPERATOR",
        action="CONFIG_OVERRIDE",
        entity_type="SYSTEM_PARAM",
        entity_id="MAX_REVIEWS"
    )

    # Tamper with stored action in database
    e.action = "MALICIOUS_TAMPER_ACTION"
    db.commit()

    is_valid, total, verified, tampered_id, msg = AuditService.verify_audit_trail_integrity(db)
    assert is_valid is False
    assert "Tamper detected" in msg or "Hash chain broken" in msg
