"""Cryptographic Append-Only Audit Trail Service."""
import hashlib
import json
import uuid
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import AuditLog


class AuditService:
    """Provides append-only cryptographic chained audit logging."""

    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    @classmethod
    def log_event(
        cls,
        db: Session,
        user_id: str,
        action: str,
        entity_type: str,
        entity_id: str,
        actor_role: str = "EXAMINER",
        status: str = "SUCCESS",
        correlation_id: Optional[str] = None,
        before_after: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        analysis_run_id: Optional[str] = None,
        dataset_import_id: Optional[str] = None
    ) -> AuditLog:
        # 1. Fetch latest audit log for previous hash
        latest = db.query(AuditLog).filter(AuditLog.integrity_hash.isnot(None)).order_by(AuditLog.timestamp.desc(), AuditLog.created_at.desc()).first()
        prev_hash = latest.integrity_hash if (latest and latest.integrity_hash) else cls.GENESIS_HASH

        ts = datetime.now(timezone.utc)
        ts_str = ts.strftime("%Y-%m-%dT%H:%M:%SZ")

        payload_str = json.dumps({
            "prev_hash": prev_hash,
            "ts": ts_str,
            "user_id": user_id,
            "actor_role": actor_role,
            "action": action,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "status": status,
            "correlation_id": correlation_id,
            "before_after": before_after or {},
            "metadata": metadata or {}
        }, sort_keys=True)

        current_hash = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()

        entry = AuditLog(
            user_id=user_id,
            actor_role=actor_role,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            timestamp=ts,
            status=status,
            correlation_id=correlation_id,
            before_after_json=before_after,
            metadata_json=metadata,
            integrity_hash=current_hash,
            previous_hash=prev_hash,
            analysis_run_id=uuid.UUID(analysis_run_id) if analysis_run_id else None,
            dataset_import_id=uuid.UUID(dataset_import_id) if dataset_import_id else None
        )

        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    @classmethod
    def query_logs(
        cls,
        db: Session,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        user_id: Optional[str] = None,
        actor_role: Optional[str] = None,
        action: Optional[str] = None,
        entity_type: Optional[str] = None,
        entity_id: Optional[str] = None,
        status: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[AuditLog], int]:
        query = db.query(AuditLog)

        if date_from:
            query = query.filter(AuditLog.timestamp >= date_from)
        if date_to:
            query = query.filter(AuditLog.timestamp <= date_to)
        if user_id:
            query = query.filter(AuditLog.user_id == user_id)
        if actor_role:
            query = query.filter(AuditLog.actor_role == actor_role)
        if action:
            query = query.filter(AuditLog.action == action)
        if entity_type:
            query = query.filter(AuditLog.entity_type == entity_type)
        if entity_id:
            query = query.filter(AuditLog.entity_id == entity_id)
        if status:
            query = query.filter(AuditLog.status == status)
        if correlation_id:
            query = query.filter(AuditLog.correlation_id == correlation_id)

        total_count = query.count()
        logs = query.order_by(AuditLog.timestamp.desc(), AuditLog.created_at.desc()).offset(offset).limit(limit).all()
        return logs, total_count

    @classmethod
    def verify_audit_trail_integrity(cls, db: Session) -> Tuple[bool, int, int, Optional[str], str]:
        records = db.query(AuditLog).filter(AuditLog.integrity_hash.isnot(None)).order_by(AuditLog.timestamp.asc(), AuditLog.created_at.asc()).all()
        if not records:
            return True, 0, 0, None, "No audit events recorded."

        expected_prev = cls.GENESIS_HASH
        verified_count = 0

        for r in records:
            if not r.integrity_hash:
                continue

            # Verify previous hash link
            if r.previous_hash and r.previous_hash != expected_prev:
                return False, len(records), verified_count, str(r.id), f"Hash chain broken at event {r.id}: expected prev {expected_prev[:10]}, got {r.previous_hash[:10]}"

            # Recompute current hash with normalized timestamp string
            ts_val = r.timestamp
            ts_str = ts_val.strftime("%Y-%m-%dT%H:%M:%SZ") if hasattr(ts_val, "strftime") else str(ts_val)

            payload_str = json.dumps({
                "prev_hash": r.previous_hash,
                "ts": ts_str,
                "user_id": r.user_id,
                "actor_role": r.actor_role,
                "action": r.action,
                "entity_type": r.entity_type,
                "entity_id": r.entity_id,
                "status": r.status,
                "correlation_id": r.correlation_id,
                "before_after": r.before_after_json or {},
                "metadata": r.metadata_json or {}
            }, sort_keys=True)
            recomputed = hashlib.sha256(payload_str.encode('utf-8')).hexdigest()

            if recomputed != r.integrity_hash:
                return False, len(records), verified_count, str(r.id), f"Tamper detected at event {r.id}: stored hash does not match payload."

            expected_prev = r.integrity_hash
            verified_count += 1

        return True, len(records), verified_count, None, f"All {verified_count} audit trail records cryptographically verified."
