"""Tests for Strict Ground Truth Isolation in Phase 13."""
import os
import inspect
import pytest
from app.rules.service import ExecutionGapEngine, NegativeSpaceEngine
from app.intelligence.enrichment_engine import ThreatEnrichmentEngine


def test_detection_engines_do_not_import_ground_truth():
    """Verify that detection and risk modules have zero reference to ground_truth_phase13.json."""
    import app.rules.service as rs
    import app.rules.negative_space as ns
    import app.analytics.risk_engine as re
    import app.analytics.prioritization_engine as pe

    rs_src = inspect.getsource(rs)
    ns_src = inspect.getsource(ns)
    re_src = inspect.getsource(re)
    pe_src = inspect.getsource(pe)

    for src in [rs_src, ns_src, re_src, pe_src]:
        assert "ground_truth" not in src.lower()
        assert "ground_truth_phase13.json" not in src


def test_enrichment_engine_does_not_read_ground_truth():
    """Verify that ThreatEnrichmentEngine operates solely on catalog dictionaries, not ground truth."""
    engine = ThreatEnrichmentEngine()
    assert not hasattr(engine, "ground_truth")
    assert not hasattr(engine, "ground_truth_path")
