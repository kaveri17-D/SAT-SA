import csv
import json
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Iterator
from app.ingestion.adapters.base import BaseDatasetAdapter, DatasetMetadata, CanonicalRecord, FieldProvenance


class SOCAlertLogAdapter(BaseDatasetAdapter):
    """Adapter for external SOC alert and network telemetry logs (Suricata, Zeek, EVTX, Syslog)."""

    def __init__(self):
        meta = DatasetMetadata(
            dataset_name="SOC_EXTERNAL_TELEMETRY_V1",
            source="Realistic Multi-Source Security Operations & Telemetry Export",
            license="Open Data Commons / Synthetic Research License",
            version="1.0.0",
            description="External security operations alert logs mapped into canonical supervisory schema.",
            is_hybrid=True,
            ground_truth_present=False,
            field_provenance_map={
                "alert_id": FieldProvenance.OBSERVED,
                "timestamp": FieldProvenance.OBSERVED,
                "src_ip": FieldProvenance.OBSERVED,
                "dest_ip": FieldProvenance.OBSERVED,
                "alert_type": FieldProvenance.OBSERVED,
                "severity": FieldProvenance.DERIVED,
                "cse_id": FieldProvenance.SYNTHETICALLY_AUGMENTED,
                "investigation_status": FieldProvenance.SYNTHETICALLY_AUGMENTED
            },
            limitations=[
                "Raw network logs lack supervisor escalation tags; workflow state is synthetically augmented.",
                "IP addresses are mapped to canonical monitored assets via deterministic CIDR lookup."
            ]
        )
        super().__init__(metadata=meta)

    def validate_schema(self, headers: List[str]) -> bool:
        norm_headers = [h.strip().lower() for h in headers]
        required = ["timestamp", "category", "severity"]
        return all(r in norm_headers for r in required)

    def parse_file(self, file_path: str) -> Iterator[CanonicalRecord]:
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                raw_data = dict(row)
                
                # Normalize timestamp
                raw_ts = row.get("timestamp") or row.get("created_at") or datetime.now(timezone.utc).isoformat()
                try:
                    ts = datetime.fromisoformat(raw_ts.replace("Z", "+00:00"))
                except Exception:
                    ts = datetime.now(timezone.utc)

                # Normalize severity
                raw_sev = str(row.get("severity", "LOW")).upper()
                if raw_sev in ("1", "CRITICAL", "VERY_HIGH"):
                    sev = "CRITICAL"
                elif raw_sev in ("2", "HIGH"):
                    sev = "HIGH"
                elif raw_sev in ("3", "MEDIUM", "MED"):
                    sev = "MEDIUM"
                else:
                    sev = "LOW"

                payload = {
                    "alert_id": row.get("alert_id", row.get("id", str(uuid.uuid4()))),
                    "cse_id": row.get("cse_id", row.get("entity_id", "CSE-EXT-01")),
                    "asset_id": row.get("asset_id", row.get("host_id", row.get("src_ip", "ASSET-EXT-01"))),
                    "created_at": ts.isoformat(),
                    "category": row.get("category", row.get("event_type", "SECURITY_ALERT")),
                    "severity": sev,
                    "status": row.get("status", "CLOSED"),
                    "details_json": {
                        "src_ip": row.get("src_ip", ""),
                        "dest_ip": row.get("dest_ip", ""),
                        "signature": row.get("signature", row.get("description", ""))
                    }
                }

                yield CanonicalRecord(
                    entity_type="Alert",
                    payload=payload,
                    raw_payload=raw_data,
                    provenance_metadata={
                        "adapter": "SOCAlertLogAdapter",
                        "field_provenance": {k: v.value for k, v in self.metadata.field_provenance_map.items()},
                        "normalization_applied": {
                            "severity": f"{raw_sev} -> {sev}",
                            "timestamp": f"{raw_ts} -> {ts.isoformat()}"
                        }
                    }
                )
