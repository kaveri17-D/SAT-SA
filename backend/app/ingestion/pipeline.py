import os
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models import (
    DatasetImport, DataQualityIssue, DatasetImportStatus, DataQualitySeverity,
    CSE, Asset, Analyst, Alert, Investigation, Escalation, Case, Closure, MaintenanceLog,
    AssetCriticality, AlertSeverity, DispositionType
)
from app.ingestion.adapters.base import BaseIngestionAdapter
from app.ingestion.adapters.csv_adapter import CSVIngestionAdapter
from app.ingestion.adapters.json_adapter import JSONIngestionAdapter
from app.ingestion.normalizer import DataNormalizer
from app.ingestion.quality import DataQualityAssessor, QualityMetrics
from app.ingestion.deduplicator import Deduplicator
from app.core.logging import logger


class IngestionPipeline:
    """Modular ingestion pipeline: Adapter -> Schema Detection -> Validation -> Quality -> Normalization -> Deduplication -> Canonical DB."""

    def __init__(self, db: Session = None, imported_by: str = "SYSTEM_INGEST"):
        self.db = db or SessionLocal()
        self.imported_by = imported_by
        self.normalizer = DataNormalizer()
        self.deduplicator = Deduplicator()

    def process_file(self, file_path: str, chunk_size: int = 5000) -> DatasetImport:
        """Process a CSV or JSON file through the canonical ingestion pipeline."""
        start_time = time.time()
        filename = os.path.basename(file_path)
        
        # 1. Select Adapter
        adapter: BaseIngestionAdapter
        if filename.endswith(".csv"):
            adapter = CSVIngestionAdapter(file_path)
        elif filename.endswith(".json") or filename.endswith(".jsonl"):
            adapter = JSONIngestionAdapter(file_path)
        else:
            raise ValueError(f"Unsupported ingestion file format: {filename}")

        entity_type = adapter.detect_entity_type()
        
        # 2. Create DatasetImport Provenance Record
        ds_import = DatasetImport(
            id=uuid.uuid4(),
            filename=filename,
            source=f"FILE_INGEST_{entity_type.upper()}",
            imported_at=datetime.now(timezone.utc),
            imported_by=self.imported_by,
            row_count=0,
            accepted_count=0,
            quarantined_count=0,
            status=DatasetImportStatus.PROCESSING,
            completeness_score=100.0
        )
        self.db.add(ds_import)
        self.db.commit()

        total_records = 0
        accepted_records = 0
        quarantined_records = 0
        invalid_timestamps = 0
        unmapped_cses = 0

        try:
            for batch in adapter.stream_batches(chunk_size=chunk_size):
                for record in batch:
                    total_records += 1
                    
                    # Deduplication check
                    if self.deduplicator.is_duplicate(record, entity_type):
                        continue

                    # Validate & Normalize record according to entity type
                    is_valid, normalized_obj, issue_desc = self._process_record(record, entity_type, ds_import.id)
                    
                    if is_valid and normalized_obj:
                        # Check idempotency against existing database primary key or unique foreign keys
                        if isinstance(normalized_obj, CSE):
                            existing = self.db.query(CSE).filter((CSE.id == normalized_obj.id) | (CSE.name == normalized_obj.name)).first()
                        elif isinstance(normalized_obj, Investigation):
                            existing = self.db.query(Investigation).filter((Investigation.id == normalized_obj.id) | (Investigation.alert_id == normalized_obj.alert_id)).first()
                        elif isinstance(normalized_obj, Escalation):
                            existing = self.db.query(Escalation).filter((Escalation.id == normalized_obj.id) | (Escalation.investigation_id == normalized_obj.investigation_id)).first()
                        elif isinstance(normalized_obj, Closure):
                            existing = self.db.query(Closure).filter((Closure.id == normalized_obj.id) | (Closure.case_id == normalized_obj.case_id)).first()
                        else:
                            existing = self.db.query(type(normalized_obj)).filter_by(id=normalized_obj.id).first()
                        if not existing:
                            self.db.add(normalized_obj)
                            accepted_records += 1
                        else:
                            # Already exists in DB - count as duplicate/accepted cleanly
                            accepted_records += 1
                    else:
                        quarantined_records += 1
                        if issue_desc and "timestamp" in issue_desc.lower():
                            invalid_timestamps += 1
                        if issue_desc and "cse" in issue_desc.lower():
                            unmapped_cses += 1
                        
                        # Never silently drop: Create DataQualityIssue
                        issue = DataQualityIssue(
                            id=uuid.uuid4(),
                            dataset_import_id=ds_import.id,
                            issue_type=f"INVALID_{entity_type.upper()}_RECORD",
                            field="record",
                            record_ref=str(record.get("id", f"row_{total_records}")),
                            severity=DataQualitySeverity.HIGH,
                            description=issue_desc or "Record failed validation or required fields missing."
                        )
                        self.db.add(issue)

                self.db.commit()

            # 3. Compute Data Quality Metrics & Update Provenance Record
            duration = round(time.time() - start_time, 3)
            metrics = DataQualityAssessor.compute_metrics(
                total_records=total_records,
                accepted_records=accepted_records,
                quarantined_records=quarantined_records,
                invalid_timestamps=invalid_timestamps,
                unmapped_cses=unmapped_cses,
                duplicate_records=total_records - (accepted_records + quarantined_records)
            )

            ds_import.row_count = total_records
            ds_import.accepted_count = accepted_records
            ds_import.quarantined_count = quarantined_records
            ds_import.completeness_score = metrics.completeness_pct
            ds_import.processing_duration_seconds = duration
            ds_import.status = DatasetImportStatus.COMPLETED if quarantined_records == 0 else DatasetImportStatus.QUARANTINED
            
            self.db.commit()
            logger.info(f"Ingestion finished for {filename}: {accepted_records}/{total_records} accepted in {duration}s")
            return ds_import

        except Exception as e:
            self.db.rollback()
            ds_import.status = DatasetImportStatus.FAILED
            self.db.commit()
            logger.error(f"Ingestion failed for {filename}: {str(e)}")
            raise e

    def _process_record(self, record: Dict[str, Any], entity_type: str, import_id: uuid.UUID) -> Tuple[bool, Optional[Any], Optional[str]]:
        """Normalize and convert raw dictionary record into canonical ORM model instance."""
        try:
            rec_id = uuid.UUID(str(record["id"])) if "id" in record and record["id"] else uuid.uuid4()
            
            if entity_type == "cses":
                if not record.get("name") or not record.get("sector"):
                    return False, None, "Missing required CSE fields: name or sector"
                return True, CSE(
                    id=rec_id,
                    name=str(record["name"]),
                    sector=str(record["sector"]),
                    entity_type=str(record.get("entity_type", "OPERATOR")),
                    size_tier=str(record.get("size_tier", "TIER_1"))
                ), None

            elif entity_type == "assets":
                if not record.get("cse_id") or not record.get("name"):
                    return False, None, "Missing required Asset fields: cse_id or name"
                return True, Asset(
                    id=rec_id,
                    cse_id=uuid.UUID(str(record["cse_id"])),
                    name=str(record["name"]),
                    asset_type=str(record.get("asset_type", "GENERIC")),
                    criticality=self.normalizer.normalize_criticality(record.get("criticality")),
                    status=str(record.get("status", "ACTIVE"))
                ), None

            elif entity_type == "alerts":
                if not record.get("cse_id") or not record.get("asset_id"):
                    return False, None, "Missing required Alert fields: cse_id or asset_id"
                
                created_at = self.normalizer.normalize_timestamp(record.get("created_at"))
                if not created_at:
                    return False, None, "Invalid or unparseable alert timestamp"

                return True, Alert(
                    id=rec_id,
                    cse_id=uuid.UUID(str(record["cse_id"])),
                    asset_id=uuid.UUID(str(record["asset_id"])),
                    source_system=str(record.get("source_system", "SIEM")),
                    category=str(record.get("category", "UNSPECIFIED")),
                    severity=self.normalizer.normalize_severity(record.get("severity") or record.get("raw_severity")),
                    raw_severity=str(record.get("raw_severity") or record.get("severity") or "UNKNOWN"),
                    status=str(record.get("status", "OPEN")),
                    created_at=created_at
                ), None

            elif entity_type == "investigations":
                if not record.get("alert_id"):
                    return False, None, "Missing required Investigation field: alert_id"
                
                started_at = self.normalizer.normalize_timestamp(record.get("started_at"))
                if not started_at:
                    return False, None, "Invalid investigation started_at timestamp"

                dur = int(record["duration_seconds"]) if record.get("duration_seconds") and str(record["duration_seconds"]).isdigit() else None
                analyst_id = uuid.UUID(str(record["analyst_id"])) if record.get("analyst_id") else None

                return True, Investigation(
                    id=rec_id,
                    alert_id=uuid.UUID(str(record["alert_id"])),
                    analyst_id=analyst_id,
                    started_at=started_at,
                    ended_at=self.normalizer.normalize_timestamp(record.get("ended_at")),
                    duration_seconds=dur,
                    notes=str(record.get("notes", "")),
                    outcome=str(record.get("outcome", "CLOSED"))
                ), None

            elif entity_type == "escalations":
                if not record.get("investigation_id"):
                    return False, None, "Missing required Escalation field: investigation_id"
                return True, Escalation(
                    id=rec_id,
                    investigation_id=uuid.UUID(str(record["investigation_id"])),
                    escalated_to=str(record.get("escalated_to", "SOC_LEAD")),
                    escalated_at=self.normalizer.normalize_timestamp(record.get("escalated_at")) or datetime.now(timezone.utc),
                    reason=str(record.get("reason", ""))
                ), None

            elif entity_type == "cases":
                if not record.get("cse_id"):
                    return False, None, "Missing required Case field: cse_id"
                return True, Case(
                    id=rec_id,
                    cse_id=uuid.UUID(str(record["cse_id"])),
                    status=str(record.get("status", "OPEN")),
                    opened_at=self.normalizer.normalize_timestamp(record.get("opened_at")) or datetime.now(timezone.utc),
                    closed_at=self.normalizer.normalize_timestamp(record.get("closed_at"))
                ), None

            elif entity_type == "closures":
                if not record.get("case_id"):
                    return False, None, "Missing required Closure field: case_id"
                return True, Closure(
                    id=rec_id,
                    case_id=uuid.UUID(str(record["case_id"])),
                    disposition_type=self.normalizer.normalize_disposition(record.get("disposition_type")),
                    closed_by=str(record.get("closed_by", "SYSTEM")),
                    closed_at=self.normalizer.normalize_timestamp(record.get("closed_at")) or datetime.now(timezone.utc),
                    justification=str(record.get("justification", ""))
                ), None

            elif entity_type == "analysts":
                if not record.get("cse_id") or not record.get("handle"):
                    return False, None, "Missing required Analyst fields: cse_id or handle"
                return True, Analyst(
                    id=rec_id,
                    cse_id=uuid.UUID(str(record["cse_id"])),
                    handle=str(record["handle"]),
                    role=str(record.get("role", "ANALYST_L1"))
                ), None

            elif entity_type == "maintenance_logs":
                if not record.get("cse_id"):
                    return False, None, "Missing required MaintenanceLog field: cse_id"
                asset_id = uuid.UUID(str(record["asset_id"])) if record.get("asset_id") else None
                return True, MaintenanceLog(
                    id=rec_id,
                    cse_id=uuid.UUID(str(record["cse_id"])),
                    asset_id=asset_id,
                    maintenance_ref=str(record.get("maintenance_ref", "MAINT_REF_UNSPECIFIED")),
                    start_time=self.normalizer.normalize_timestamp(record.get("start_time")) or datetime.now(timezone.utc),
                    end_time=self.normalizer.normalize_timestamp(record.get("end_time")) or datetime.now(timezone.utc),
                    reason=str(record.get("reason", "")),
                    approved_by=str(record.get("approved_by", "SYSTEM"))
                ), None

            return False, None, f"Unknown entity type {entity_type}"

        except Exception as err:
            return False, None, f"Exception normalizing record: {str(err)}"
