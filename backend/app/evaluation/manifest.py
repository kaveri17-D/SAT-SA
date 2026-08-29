import json
import os
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional


@dataclass
class ExperimentManifest:
    """Machine-readable experiment manifest documenting reproducibility metadata."""
    experiment_id: str
    timestamp: str
    dataset_identifier: str
    dataset_version: str
    seed: Optional[int]
    seeds: List[int]
    generator_configuration: Dict[str, Any]
    analysis_run_id: Optional[str]
    rule_versions: Dict[str, str]
    model_versions: Dict[str, str]
    satsa_version: str
    evaluation_version: str
    scenario_configuration: Dict[str, Any]
    metric_configuration: Dict[str, Any]
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def save(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "ExperimentManifest":
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    @classmethod
    def create(
        cls,
        experiment_id: str,
        seed: Optional[int] = None,
        seeds: Optional[List[int]] = None,
        dataset_identifier: str = "SYNTHETIC_CANONICAL_V1",
        dataset_version: str = "1.0.0",
        generator_configuration: Optional[Dict[str, Any]] = None,
        analysis_run_id: Optional[str] = None,
        rule_versions: Optional[Dict[str, str]] = None,
        model_versions: Optional[Dict[str, str]] = None,
        scenario_configuration: Optional[Dict[str, Any]] = None,
        metric_configuration: Optional[Dict[str, Any]] = None,
        notes: str = "SAT-SA Controlled Synthetic Scientific Evaluation"
    ) -> "ExperimentManifest":
        seed_list = seeds if seeds is not None else ([seed] if seed is not None else [42])
        primary_seed = seed if seed is not None else (seed_list[0] if seed_list else 42)

        default_rules = {
            "GAP-01": "1.0.0", "GAP-02": "1.0.0", "GAP-03": "1.0.0",
            "GAP-04": "1.0.0", "GAP-05": "1.0.0", "GAP-06": "1.0.0",
            "NEG-01": "1.0.0", "NEG-02": "1.0.0", "NEG-03": "1.0.0",
            "NEG-04": "1.0.0", "NEG-05": "1.0.0"
        }

        default_models = {
            "risk_engine": "1.0.0",
            "prioritization_engine": "1.0.0",
            "evidence_graph": "1.0.0"
        }

        return cls(
            experiment_id=experiment_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            dataset_identifier=dataset_identifier,
            dataset_version=dataset_version,
            seed=primary_seed,
            seeds=seed_list,
            generator_configuration=generator_configuration or {},
            analysis_run_id=analysis_run_id,
            rule_versions=rule_versions or default_rules,
            model_versions=model_versions or default_models,
            satsa_version="1.0.0-PROMPT-B",
            evaluation_version="1.0.0",
            scenario_configuration=scenario_configuration or {},
            metric_configuration=metric_configuration or {
                "top_k_thresholds": [1, 3, 5, 10, 20],
                "ranking_metrics": ["Precision@K", "Recall@K", "NDCG@K", "MAP@K"],
                "explainability_fields": [
                    "why_flagged", "expected_behaviour", "observed_behaviour",
                    "evidence", "peer_comparison", "confidence",
                    "risk_contribution", "recommendation"
                ]
            },
            notes=notes
        )
