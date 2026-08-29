import os
import tempfile
import pytest
from app.ingestion.adapters.base import FieldProvenance
from app.ingestion.adapters.soc_log_adapter import SOCAlertLogAdapter
from app.ingestion.profiler import DatasetProfiler
from app.ingestion.quality_scoring import DataQualityScorer


def test_soc_alert_log_adapter():
    """Verify external SOC log adapter maps fields to canonical SAT-SA records."""
    adapter = SOCAlertLogAdapter()
    assert adapter.metadata.is_hybrid is True
    assert adapter.metadata.field_provenance_map["alert_id"] == FieldProvenance.OBSERVED
    assert adapter.metadata.field_provenance_map["severity"] == FieldProvenance.DERIVED

    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("timestamp,category,severity,src_ip,dest_ip,description\n")
        f.write("2026-04-01T10:00:00Z,FIREWALL_DROP,1,10.0.0.1,192.168.1.1,Inbound port scan\n")
        f.write("2026-04-01T10:05:00Z,AUTH_FAILURE,2,10.0.0.2,192.168.1.5,Failed SSH login\n")
        temp_path = f.name

    try:
        records = list(adapter.parse_file(temp_path))
        assert len(records) == 2
        
        r1 = records[0]
        assert r1.entity_type == "Alert"
        assert r1.payload["severity"] == "CRITICAL"
        assert r1.payload["category"] == "FIREWALL_DROP"
        assert r1.provenance_metadata["adapter"] == "SOCAlertLogAdapter"

        r2 = records[1]
        assert r2.payload["severity"] == "HIGH"
        assert r2.payload["category"] == "AUTH_FAILURE"
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def test_dataset_profiler_and_quality_scorer():
    """Verify dataset profiling and 6-dimension data quality scoring."""
    with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as f:
        f.write("cse_id,asset_id,created_at,severity,category\n")
        f.write("CSE-01,ASSET-01,2026-03-01T12:00:00Z,CRITICAL,FIREWALL\n")
        f.write("CSE-01,ASSET-02,2026-03-01T13:00:00Z,HIGH,EDR\n")
        f.write("CSE-02,ASSET-03,2026-03-01T14:00:00Z,MEDIUM,SIEM\n")
        f.write("CSE-02,ASSET-03,2026-03-01T14:00:00Z,MEDIUM,SIEM\n")  # duplicate
        temp_path = f.name

    try:
        profile = DatasetProfiler.profile_csv(temp_path)
        assert profile.total_records == 4
        assert profile.duplicate_record_count == 1
        assert profile.null_counts["cse_id"] == 0
        assert profile.severity_distribution["CRITICAL"] == 1

        quality = DataQualityScorer.evaluate_quality(profile)
        assert quality.overall_score >= 80.0
        assert len(quality.dimensions) == 6
        assert quality.grade in ("A", "B")
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
