"""Tests for Cryptographic Chained Audit Logging and Verification."""
import pytest
from sqlalchemy.orm import Session
from app.models import AuditLog
from app.audit.service import AuditService


def test_audit_event_logging_and_hash_chaining(db: Session):
    # Log event 1
    e1 = AuditService.log_event(
        db=db,
        user_id="EXAMINER_01",
        action="ANALYSIS_RUN_TRIGGERED",
        entity_type="ANALYSIS_RUN",
        entity_id="RUN-1001",
        actor_role="EXAMINER",
        status="SUCCESS"
    )
    assert e1.integrity_hash is not None
    assert e1.previous_hash is not None

    # Log event 2
    e2 = AuditService.log_event(
        db=db,
        user_id="EXAMINER_01",
        action="REPORT_GENERATED",
        entity_type="REPORT_SNAPSHOT",
        entity_id="REP-2001",
        actor_role="EXAMINER",
        status="SUCCESS"
    )
    assert e2.previous_hash == e1.integrity_hash

    # Verify chain
    is_valid, total, verified, tampered_id, msg = AuditService.verify_audit_trail_integrity(db)
    assert is_valid is True
    assert verified >= 2
    assert tampered_id is None


def test_audit_tamper_detection(db: Session):
    # Log event
    e = AuditService.log_event(
        db=db,
        user_id="USER_LEGIT",
        action="CONFIG_UPDATE",
        entity_type="SETTING",
        entity_id="MAX_RETRIES",
        before_after={"old": 3, "new": 5}
    )

    # Tamper with stored user_id
    e.user_id = "MALICIOUS_IMPOSTOR"
    db.commit()

    is_valid, total, verified, tampered_id, msg = AuditService.verify_audit_trail_integrity(db)
    assert is_valid is False
    assert "Tamper detected" in msg or "Hash chain broken" in msg


def test_audit_query_and_pagination(db: Session):
    for i in range(10):
        AuditService.log_event(
            db=db,
            user_id="PAGINATION_USER",
            action=f"ACTION_{i}",
            entity_type="RESOURCE",
            entity_id=f"RES_{i}"
        )

    logs, total = AuditService.query_logs(db=db, user_id="PAGINATION_USER", limit=5, offset=0)
    assert total == 10
    assert len(logs) == 5

    logs_p2, total2 = AuditService.query_logs(db=db, user_id="PAGINATION_USER", limit=5, offset=5)
    assert len(logs_p2) == 5
    assert logs[0].id != logs_p2[0].id
