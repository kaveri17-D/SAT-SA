import os
import tempfile
import pytest
from datetime import datetime
from app.ingestion.generator.config import GeneratorConfig
from app.ingestion.generator.engine import SyntheticDatasetGenerator
from app.ingestion.generator.exporters import export_dataset_to_csv
from app.ingestion.generator.ground_truth import ScenarioClass, ScenarioType


def test_generator_determinism():
    """Verify that running the generator with the same seed produces identical dataset outputs."""
    config1 = GeneratorConfig(seed=12345, num_cses=5, total_alerts=1000)
    gen1 = SyntheticDatasetGenerator(config1)
    data1 = gen1.generate()

    config2 = GeneratorConfig(seed=12345, num_cses=5, total_alerts=1000)
    gen2 = SyntheticDatasetGenerator(config2)
    data2 = gen2.generate()

    assert len(data1["cses"]) == len(data2["cses"])
    assert len(data1["assets"]) == len(data2["assets"])
    assert len(data1["alerts"]) == len(data2["alerts"])
    assert len(data1["investigations"]) == len(data2["investigations"])
    
    # Assert exact ID matching on first CSE and alert
    assert data1["cses"][0].id == data2["cses"][0].id
    assert data1["alerts"][0].id == data2["alerts"][0].id


def test_referential_integrity():
    """Verify foreign key relationships across generated entities."""
    config = GeneratorConfig.baseline_preset()
    generator = SyntheticDatasetGenerator(config)
    data = generator.generate()

    cse_ids = {c.id for c in data["cses"]}
    asset_ids = {a.id for a in data["assets"]}
    alert_ids = {alt.id for alt in data["alerts"]}
    inv_ids = {inv.id for inv in data["investigations"]}
    case_ids = {cs.id for cs in data["cases"]}

    # Assets -> CSE
    for asset in data["assets"]:
        assert asset.cse_id in cse_ids

    # Alerts -> CSE & Asset
    for alert in data["alerts"]:
        assert alert.cse_id in cse_ids
        assert alert.asset_id in asset_ids

    # Investigations -> Alert
    for inv in data["investigations"]:
        assert inv.alert_id in alert_ids

    # Escalations -> Investigation
    for esc in data["escalations"]:
        assert esc.investigation_id in inv_ids

    # Closures -> Case
    for closure in data["closures"]:
        assert closure.case_id in case_ids


def test_timestamp_chronological_consistency():
    """Verify temporal ordering: alert.created_at <= inv.started_at <= inv.ended_at."""
    config = GeneratorConfig.baseline_preset()
    generator = SyntheticDatasetGenerator(config)
    data = generator.generate()

    alerts_by_id = {alt.id: alt for alt in data["alerts"]}
    invs_by_id = {inv.id: inv for inv in data["investigations"]}

    for inv in data["investigations"]:
        parent_alert = alerts_by_id[inv.alert_id]
        assert parent_alert.created_at <= inv.started_at
        if inv.ended_at:
            assert inv.started_at <= inv.ended_at

    for esc in data["escalations"]:
        parent_inv = invs_by_id[esc.investigation_id]
        assert parent_inv.started_at <= esc.escalated_at


def test_scenario_injection_and_ground_truth_isolation():
    """Verify that ground-truth scenarios are present and isolated from domain records."""
    config = GeneratorConfig.baseline_preset()
    generator = SyntheticDatasetGenerator(config)
    data = generator.generate()

    manifest = data["manifest"]
    scenarios = manifest.ground_truth_scenarios
    assert len(scenarios) > 0

    # Ensure scenario classes are populated
    classes_found = {s.scenario_class for s in scenarios}
    assert ScenarioClass.EXECUTION_GAP in classes_found
    assert ScenarioClass.NEGATIVE_SPACE in classes_found
    assert ScenarioClass.PEER_ANOMALY in classes_found
    assert ScenarioClass.LEGITIMATE_EXCEPTION in classes_found

    # Ground truth tags must NOT be present as attribute fields on Alert model instances
    first_alert = data["alerts"][0]
    assert not hasattr(first_alert, "scenario_class")
    assert not hasattr(first_alert, "scenario_type")


def test_legitimate_exceptions_generated():
    """Verify legitimate exception scenarios (maintenance logs, decommissioned assets) exist."""
    config = GeneratorConfig.baseline_preset()
    generator = SyntheticDatasetGenerator(config)
    data = generator.generate()

    exceptions = [s for s in data["manifest"].ground_truth_scenarios if s.is_legitimate_exception]
    assert len(exceptions) >= 2

    # Verify maintenance logs generated
    assert len(data["maintenance_logs"]) >= 1
    maint = data["maintenance_logs"][0]
    assert "asset_id" in maint
    assert "maintenance_ref" in maint


def test_csv_export():
    """Verify dataset export to CSV directory."""
    config = GeneratorConfig(seed=999, num_cses=3, total_alerts=100)
    generator = SyntheticDatasetGenerator(config)
    data = generator.generate()

    with tempfile.TemporaryDirectory() as tmpdir:
        export_dataset_to_csv(data, tmpdir)
        
        expected_files = [
            "cses.csv", "assets.csv", "analysts.csv", "alerts.csv",
            "investigations.csv", "escalations.csv", "cases.csv",
            "closures.csv", "maintenance_logs.csv", "ground_truth.json"
        ]
        for fname in expected_files:
            fpath = os.path.join(tmpdir, fname)
            assert os.path.exists(fpath)
            assert os.path.getsize(fpath) > 0
