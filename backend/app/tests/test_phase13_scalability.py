"""Tests for Progressive Scalability Benchmarking."""
import pytest
from app.intelligence.scalability import Phase13ScalabilityBenchmark


def test_scalability_tier_1k():
    res = Phase13ScalabilityBenchmark.run_tier(1000)
    assert res["valid_records"] == 1000
    assert res["total_time_seconds"] < 1.0
    assert res["peak_memory_mb"] < 25.0


def test_scalability_tier_10k():
    res = Phase13ScalabilityBenchmark.run_tier(10000)
    assert res["valid_records"] == 10000
    assert res["total_time_seconds"] < 5.0
    assert res["lookup_throughput_lookups_per_sec"] > 50000.0
