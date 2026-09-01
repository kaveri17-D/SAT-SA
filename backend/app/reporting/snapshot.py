"""Report Snapshot & Cryptographic Verification Engine."""
import json
import hashlib
import uuid
from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models import ReportSnapshot, ReportEvidenceReference, ReportType, ReportStatus


class SnapshotManager:
    """Manages immutable report snapshot creation, persistence, and integrity verification."""

    @staticmethod
    def create_and_sign_snapshot(
        db: Session,
        analysis_run_id: str,
        report_type: ReportType,
        summary: Dict[str, Any],
        content: Dict[str, Any],
        evidence_refs: list,
        cse_id: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        generated_by: str = "SYSTEM_EXAMINER",
        metadata: Optional[Dict[str, Any]] = None
    ) -> ReportSnapshot:
        # Canonical JSON string for deterministic SHA-256 hash
        canonical_content = json.dumps(content, sort_keys=True, separators=(',', ':'))
        sha256_hash = hashlib.sha256(canonical_content.encode('utf-8')).hexdigest()

        report_number = f"REP-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"

        snapshot = ReportSnapshot(
            report_number=report_number,
            report_type=report_type,
            status=ReportStatus.COMPLETED,
            title=title or content.get("report_header", {}).get("title", f"{report_type.value} Report"),
            description=description,
            analysis_run_id=uuid.UUID(analysis_run_id),
            cse_id=uuid.UUID(cse_id) if cse_id else None,
            generated_at=datetime.now(timezone.utc),
            generated_by=generated_by,
            schema_version="1.0.0",
            system_version="1.0.0",
            data_foundation_version="1.0.0",
            sha256_checksum=sha256_hash,
            is_tampered=False,
            summary_json=summary,
            content_json=content,
            metadata_json=metadata or {}
        )
        db.add(snapshot)
        db.flush()

        # Add evidence references
        for ref in evidence_refs:
            ev_ref = ReportEvidenceReference(
                report_id=snapshot.id,
                finding_id=uuid.UUID(ref["finding_id"]) if ref.get("finding_id") else None,
                evidence_id=uuid.UUID(ref["evidence_id"]) if ref.get("evidence_id") else None,
                evidence_type=ref.get("evidence_type", "UNKNOWN"),
                source_table=ref.get("source_table", "UNKNOWN"),
                source_record_id=str(ref.get("source_record_id", "")),
                relevance=ref.get("relevance", "HIGH"),
                description=ref.get("description", ""),
                provenance_json=ref.get("provenance", {})
            )
            db.add(ev_ref)

        db.commit()
        db.refresh(snapshot)
        return snapshot

    @staticmethod
    def verify_integrity(snapshot: ReportSnapshot) -> Tuple[bool, str]:
        canonical_content = json.dumps(snapshot.content_json, sort_keys=True, separators=(',', ':'))
        computed_hash = hashlib.sha256(canonical_content.encode('utf-8')).hexdigest()
        is_valid = (computed_hash == snapshot.sha256_checksum)
        if not is_valid:
            snapshot.is_tampered = True
            return False, f"Tamper detected: Computed hash {computed_hash[:12]} does not match stored {snapshot.sha256_checksum[:12]}"
        return True, "Integrity verified: SHA-256 checksum matches snapshot payload."
