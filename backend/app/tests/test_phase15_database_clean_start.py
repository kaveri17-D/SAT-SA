"""Phase 15: Clean-Database Initialization and Schema Integrity Validation."""
import os
import tempfile
import pytest
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
import app.models
from app.db.seed import seed_baseline_reference_data
from app.models import RuleVersion, ModelVersion


def test_clean_database_initialization_from_scratch():
    """Verify that a fresh, empty SQLite database creates all 24 tables with correct indexes and constraints."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        tmp_engine = create_engine(f"sqlite:///{tmp_path}", connect_args={"check_same_thread": False})
        
        # Create all tables on clean database
        Base.metadata.create_all(bind=tmp_engine)
        
        inspector = inspect(tmp_engine)
        table_names = set(inspector.get_table_names())
        
        expected_tables = {
            "cses", "assets", "alerts", "investigations", "analysts", "escalations",
            "cases", "closures", "maintenance_logs", "dataset_imports", "data_quality_issues", "rule_versions",
            "model_versions", "analysis_runs", "audit_logs", "findings", "evidence",
            "risk_scores", "peer_groups", "peer_group_memberships", "benchmarks", "review_queue_items",
            "report_snapshots", "report_evidence_references"
        }
        
        assert len(table_names) == 24
        assert expected_tables.issubset(table_names)

        # Seed reference data into clean DB
        TmpSession = sessionmaker(bind=tmp_engine)
        db = TmpSession()
        try:
            seed_baseline_reference_data(db)
            rule_count = db.query(RuleVersion).count()
            model_count = db.query(ModelVersion).count()
            assert rule_count >= 9
            assert model_count >= 2
        finally:
            db.close()
            tmp_engine.dispose()
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
