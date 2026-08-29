import json
import os
import tempfile
import uuid
import pytest
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, Base, engine
from app.models import DatasetImport, DataQualityIssue, Alert, CSE, Asset, AlertSeverity, DatasetImportStatus
from app.ingestion.pipeline import IngestionPipeline
from app.ingestion.normalizer import DataNormalizer
from app.ingestion.quality import DataQualityAssessor
from app.ingestion.generator.config import GeneratorConfig
from app.ingestion.generator.engine import SyntheticDatasetGenerator
from app.ingestion.generator.exporters import export_dataset_to_csv


def test_severity_and_timestamp_normalization():
    """Test severity and timestamp normalization rules."""
    norm = DataNormalizer()
    assert norm.normalize_severity("P1") == AlertSeverity.CRITICAL
    assert norm.normalize_severity("Sev-1") == AlertSeverity.CRITICAL
    assert norm.normalize_severity("Critical") == AlertSeverity.CRITICAL
    assert norm.normalize_severity("P2") == AlertSeverity.HIGH
    assert norm.normalize_severity("SEV-3") == AlertSeverity.MEDIUM
    assert norm.normalize_severity("INFORMATIONAL") == AlertSeverity.INFO

    ts = norm.normalize_timestamp("2026-01-15T10:30:00Z")
    assert ts is not None
    assert ts.year == 2026
    assert ts.month == 1


def test_confidence_modifier_calculation():
    """Test reusable confidence modifier propagation from completeness score."""
    assessor = DataQualityAssessor()
    assert assessor.calculate_confidence_modifier(100.0) == 1.0
    assert assessor.calculate_confidence_modifier(95.0) == 1.0
    assert assessor.calculate_confidence_modifier(85.0) == 0.85
    assert assessor.calculate_confidence_modifier(65.0) == 0.65
    assert assessor.calculate_confidence_modifier(40.0) == 0.40


def test_ingestion_pipeline_with_phase3_exports():
    """Test full ingestion pipeline using Phase 3 generated exports."""
    config = GeneratorConfig(seed=777, num_cses=3, total_alerts=100)
    generator = SyntheticDatasetGenerator(config)
    data = generator.generate()

    with tempfile.TemporaryDirectory() as tmpdir:
        export_dataset_to_csv(data, tmpdir)

        db: Session = SessionLocal()
        Base.metadata.create_all(bind=engine)
        try:
            pipeline = IngestionPipeline(db=db, imported_by="test_examiner")
            
            # Ingest in dependency order
            cses_import = pipeline.process_file(os.path.join(tmpdir, "cses.csv"))
            assert cses_import.status in (DatasetImportStatus.COMPLETED, DatasetImportStatus.QUARANTINED)
            assert cses_import.row_count > 0
            assert cses_import.accepted_count > 0

            assets_import = pipeline.process_file(os.path.join(tmpdir, "assets.csv"))
            assert assets_import.row_count > 0

            alerts_import = pipeline.process_file(os.path.join(tmpdir, "alerts.csv"))
            assert alerts_import.row_count > 0
            assert alerts_import.accepted_count > 0

            # Idempotent re-import check: Re-importing alerts.csv should not crash or duplicate records
            reimport_alerts = pipeline.process_file(os.path.join(tmpdir, "alerts.csv"))
            assert reimport_alerts.row_count == alerts_import.row_count

        finally:
            db.close()


def test_malformed_records_and_quarantine():
    """Test that malformed rows produce DataQualityIssue records and are quarantined, never silently dropped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        csv_path = os.path.join(tmpdir, "malformed_alerts.csv")
        with open(csv_path, "w", encoding="utf-8") as f:
            f.write("id,cse_id,asset_id,source_system,category,severity,created_at\n")
            # Row 1: Valid
            u_cse = str(uuid.uuid4())
            u_asset = str(uuid.uuid4())
            f.write(f"{uuid.uuid4()},{u_cse},{u_asset},SIEM,MALWARE,P1,2026-01-15T12:00:00Z\n")
            # Row 2: Malformed (missing cse_id)
            f.write(f"{uuid.uuid4()},,,SIEM,MALWARE,P1,2026-01-15T12:00:00Z\n")

        db: Session = SessionLocal()
        try:
            pipeline = IngestionPipeline(db=db, imported_by="quarantine_test")
            result = pipeline.process_file(csv_path)

            assert result.row_count == 2
            assert result.accepted_count == 1
            assert result.quarantined_count == 1

            # Check DataQualityIssue created
            issues = db.query(DataQualityIssue).filter(DataQualityIssue.dataset_import_id == result.id).all()
            assert len(issues) == 1
            assert "Missing required Alert fields" in issues[0].description
        finally:
            db.close()


def test_json_file_ingestion():
    """Test JSON array ingestion adapter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        json_path = os.path.join(tmpdir, "test_cses.json")
        sample_cses = [
            {"id": str(uuid.uuid4()), "name": f"JSON CSE {uuid.uuid4()}", "sector": "BANKING", "entity_type": "BANK", "size_tier": "TIER_1"}
        ]
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(sample_cses, f)

        db: Session = SessionLocal()
        try:
            pipeline = IngestionPipeline(db=db, imported_by="json_test")
            result = pipeline.process_file(json_path)
            assert result.accepted_count == 1
        finally:
            db.close()
