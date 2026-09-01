"""Tests for Phase 13 Benchmark Dataset and 10 Realistic Scenarios."""
import json
import os
import pytest
from app.intelligence.config import get_data_dir
from app.intelligence.benchmark_builder import Phase13BenchmarkBuilder


def test_all_10_scenarios_validation():
    data_dir = get_data_dir()
    scenario_dir = os.path.join(data_dir, "benchmark", "scenarios")
    assert os.path.exists(scenario_dir)
    files = [f for f in os.listdir(scenario_dir) if f.endswith(".json")]
    assert len(files) == 10

    for f_name in files:
        with open(os.path.join(scenario_dir, f_name), "r", encoding="utf-8") as f:
            data = json.load(f)
            assert "scenario_id" in data
            assert "name" in data
            assert "category" in data
            assert "expected_condition" in data
            assert "expected_threat_context" in data
            assert "ground_truth_label" in data


def test_benchmark_consolidated_dataset():
    data_dir = get_data_dir()
    with open(os.path.join(data_dir, "benchmark", "satsa_phase13_benchmark_dataset.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
    assert data["dataset_name"] == "SAT-SA BENCHMARK DATASET — PHASE 13"
    assert len(data["scenarios"]) == 10
