import ast
import os
import glob
import pytest
from app.evaluation.metrics import (
    BinaryClassificationMetrics, RankingMetrics,
    PrioritizationReductionMetrics, ExplainabilityCompletenessMetrics,
    MultiSeedAggregator
)
from app.evaluation.manifest import ExperimentManifest
from app.evaluation.sensitivity import ThresholdSensitivityHarness
from app.evaluation.robustness import RobustnessHarness


def test_ground_truth_isolation():
    """Mandatory Audit: Prove that production detection/analytics modules NEVER import ground truth.
    
    Ground truth may ONLY be used in:
    - app/evaluation/
    - app/analytics/evaluator.py (legacy eval wrapper)
    - app/tests/
    - app/ingestion/generator/ (which synthesizes ground truth alongside data)
    """
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    
    production_dirs = [
        os.path.join(backend_root, "app", "rules"),
        os.path.join(backend_root, "app", "evidence"),
        os.path.join(backend_root, "app", "api"),
        os.path.join(backend_root, "app", "models"),
    ]
    
    production_files = [
        os.path.join(backend_root, "app", "analytics", "risk_engine.py"),
        os.path.join(backend_root, "app", "analytics", "prioritization_engine.py"),
        os.path.join(backend_root, "app", "analytics", "graph_engine.py"),
        os.path.join(backend_root, "app", "ingestion", "pipeline.py"),
        os.path.join(backend_root, "app", "ingestion", "quality.py"),
        os.path.join(backend_root, "app", "ingestion", "normalizer.py"),
    ]
    
    for pdir in production_dirs:
        for pyfile in glob.glob(os.path.join(pdir, "*.py")):
            production_files.append(pyfile)
            
    forbidden_tokens = ["ground_truth", "GroundTruth", "ground_truth_scenarios"]
    
    for filepath in production_files:
        with open(filepath, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=filepath)
            
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "ground_truth" not in alias.name, f"Production file '{filepath}' imports ground truth module '{alias.name}'"
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                assert "ground_truth" not in module, f"Production file '{filepath}' imports from ground truth module '{module}'"
                for alias in node.names:
                    assert "ground_truth" not in alias.name.lower(), f"Production file '{filepath}' imports '{alias.name}' from '{module}'"


def test_metric_correctness():
    """Verify precision, recall, f1, and false positive rate calculations."""
    m = BinaryClassificationMetrics.compute(tp=10, fp=2, fn=0, tn=88)
    assert m.precision == round(10 / 12, 4)
    assert m.recall == 1.0
    assert m.false_positive_rate == round(2 / 90, 4)
    assert m.detection_rate == 1.0
    assert m.f1_score == round((2 * (10/12) * 1.0) / ((10/12) + 1.0), 4)

    # Zero edge cases (0 TP, 0 FP, 0 FN -> perfect clean performance)
    m_zero = BinaryClassificationMetrics.compute(tp=0, fp=0, fn=0, tn=100)
    assert m_zero.precision == 1.0
    assert m_zero.recall == 1.0
    assert m_zero.f1_score == 1.0
    assert m_zero.false_positive_rate == 0.0


def test_ranking_metrics():
    """Verify Top-K Recall, Precision@K, NDCG@K, and Average Precision calculations."""
    ranked = ["item_a", "item_b", "item_c", "item_d", "item_e"]
    relevant = {"item_a", "item_c"}  # 2 relevant items total

    rm = RankingMetrics.compute(ranked_candidate_ids=ranked, ground_truth_relevant_ids=relevant, k_values=[1, 3, 5])
    
    # Top-1: item_a is relevant
    assert rm.precision_at_k[1] == 1.0
    assert rm.recall_at_k[1] == 0.5  # 1 out of 2 relevant
    
    # Top-3: item_a (hit), item_b (miss), item_c (hit) -> 2/3 precision, 2/2 recall
    assert rm.precision_at_k[3] == round(2 / 3, 4)
    assert rm.recall_at_k[3] == 1.0
    assert rm.average_precision_at_k[3] > 0.8
    assert rm.ndcg_at_k[3] > 0.8


def test_prioritization_reduction_and_diversity():
    """Verify sample reduction, coverage metrics, and Herfindahl concentration calculations."""
    class DummyFinding:
        def __init__(self, fid, cse_id, rule_id, sev):
            self.id = fid
            self.cse_id = cse_id
            self.rule_id = rule_id
            self.severity = sev

    class DummyQueueItem:
        def __init__(self, fid, cse_id, rule_id):
            self.finding_id = fid
            self.cse_id = cse_id
            self.rule_id = rule_id

    # 100 candidate findings across 5 CSEs
    cands = []
    for i in range(100):
        cands.append(DummyFinding(f"f_{i}", f"cse_{i % 5}", f"GAP-0{i % 3 + 1}", "CRITICAL" if i < 10 else "LOW"))

    # Queue of 10 items evenly distributed across CSEs
    queue = []
    for i in range(10):
        queue.append(DummyQueueItem(f"f_{i}", f"cse_{i % 5}", f"GAP-0{i % 3 + 1}"))

    prm = PrioritizationReductionMetrics.compute(candidate_findings=cands, queue_items=queue)
    
    assert prm.total_candidate_findings == 100
    assert prm.recommended_queue_size == 10
    assert prm.review_sample_reduction == 0.90
    assert prm.critical_finding_coverage == 1.0  # All 10 critical findings captured
    assert prm.unique_cses_in_queue == 5
    assert prm.cse_coverage == 1.0
    # Balanced distribution (2 items per CSE) yields HHI = 5 * (0.2)^2 = 0.20
    assert prm.herfindahl_concentration_index == 0.20


def test_explainability_completeness_and_placeholder_rejection():
    """Verify explainability verification across 8 dimensions and placeholder rejection."""
    class DummyFinding:
        def __init__(self, reason, exp, obs, refs, conf, risk, rec):
            self.id = "f1"
            self.reason = reason
            self.expected_behaviour = exp
            self.observed_behaviour = obs
            self.evidence_refs = refs
            self.confidence = conf
            self.risk_score = risk
            self.recommendation = rec

    # 1. Complete finding
    f_good = DummyFinding(
        reason="Supervisory failure",
        exp="Expected escalation",
        obs="Closed without escalation",
        refs=[{"evidence_id": "ev_1"}],
        conf=0.95,
        risk=30.0,
        rec="Reopen for review"
    )
    res_good = ExplainabilityCompletenessMetrics.compute([f_good])
    assert res_good.completeness_percentage == 100.0
    assert res_good.fully_explained_findings == 1

    # 2. Finding with "N/A" placeholders
    f_placeholder = DummyFinding(
        reason="N/A",
        exp="TODO",
        obs="Closed without escalation",
        refs=[],
        conf=0.95,
        risk=30.0,
        rec=""
    )
    res_bad = ExplainabilityCompletenessMetrics.compute([f_placeholder])
    assert res_bad.completeness_percentage == 0.0
    assert res_bad.placeholder_rejection_count >= 1


def test_multi_seed_aggregator_statistics():
    """Verify multi-seed distribution statistics calculation."""
    vals = [1.0, 0.95, 0.98, 1.0, 0.97]
    stats = MultiSeedAggregator.aggregate(vals)
    assert 0.95 <= stats["mean"] <= 1.0
    assert stats["min"] == 0.95
    assert stats["max"] == 1.0
    assert stats["std"] > 0.0
    assert stats["ci_95_lower"] <= stats["mean"] <= stats["ci_95_upper"]


def test_threshold_boundary_sensitivity():
    """Verify threshold boundary sensitivity evaluation."""
    rep = ThresholdSensitivityHarness.run_sensitivity_analysis()
    assert rep.total_boundary_tests >= 6
    assert rep.consistency_rate == 100.0
    for p in rep.test_points:
        assert p.is_consistent is True


def test_robustness_safeguards():
    """Verify zero-variance, outlier skew, null safety, and maintenance suppression safeguards."""
    rep = RobustnessHarness.run_robustness_tests()
    assert rep.total_robustness_tests >= 6
    assert rep.pass_rate == 100.0
    assert rep.failed_tests == 0


def test_experiment_manifest_serialization(tmp_path):
    """Verify experiment manifest creation, schema, and JSON persistence."""
    man = ExperimentManifest.create(
        experiment_id="TEST-EXP-01",
        seed=42,
        dataset_identifier="TEST_SET_V1"
    )
    save_file = os.path.join(tmp_path, "manifest.json")
    man.save(save_file)
    
    loaded = ExperimentManifest.load(save_file)
    assert loaded.experiment_id == "TEST-EXP-01"
    assert loaded.seed == 42
    assert loaded.dataset_identifier == "TEST_SET_V1"
    assert "GAP-01" in loaded.rule_versions


def test_deterministic_state_hasher():
    """Verify deterministic state hasher produces stable SHA-256 hash across runs."""
    from app.evaluation.reproducibility import DeterministicStateHasher
    from app.core.database import SessionLocal
    
    db = SessionLocal()
    try:
        # Test hash computation without error
        import uuid
        dummy_run_id = str(uuid.uuid4())
        hash_val = DeterministicStateHasher.compute_state_hash(db, dummy_run_id)
        assert isinstance(hash_val, str)
        assert len(hash_val) == 64
    finally:
        db.close()

