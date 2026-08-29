import enum
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional, Any


class ScenarioClass(str, enum.Enum):
    NORMAL = "NORMAL"
    EXECUTION_GAP = "EXECUTION_GAP"
    NEGATIVE_SPACE = "NEGATIVE_SPACE"
    PEER_ANOMALY = "PEER_ANOMALY"
    MIXED_SIGNAL = "MIXED_SIGNAL"
    LEGITIMATE_EXCEPTION = "LEGITIMATE_EXCEPTION"


class ScenarioType(str, enum.Enum):
    # Execution Gap scenario types
    CRITICAL_ALERT_NO_ESCALATION = "CRITICAL_ALERT_NO_ESCALATION"
    HIGH_CRITICAL_NO_INVESTIGATION = "HIGH_CRITICAL_NO_INVESTIGATION"
    HASTY_INVESTIGATION_DURATION = "HASTY_INVESTIGATION_DURATION"
    REPEATED_ALERTS_UNREMEDIATED = "REPEATED_ALERTS_UNREMEDIATED"
    INCONSISTENT_CLOSURE_DISPOSITION = "INCONSISTENT_CLOSURE_DISPOSITION"
    MISSING_WORKFLOW_TRANSITION = "MISSING_WORKFLOW_TRANSITION"

    # Negative Space scenario types
    CRITICAL_ASSET_MISSING_TELEMETRY = "CRITICAL_ASSET_MISSING_TELEMETRY"
    SUDDEN_TELEMETRY_DROP = "SUDDEN_TELEMETRY_DROP"
    MISSING_ALERT_CATEGORY = "MISSING_ALERT_CATEGORY"
    UNDER_MONITORED_CRITICAL_ASSET = "UNDER_MONITORED_CRITICAL_ASSET"
    UNEXPLAINED_MAINTENANCE_SILENCE = "UNEXPLAINED_MAINTENANCE_SILENCE"
    MISSING_REMEDIATION_EVIDENCE = "MISSING_REMEDIATION_EVIDENCE"

    # Peer Anomaly scenario types
    PEER_ESCALATION_RATE_DEVIATION = "PEER_ESCALATION_RATE_DEVIATION"
    CSE07_SUPERVISORY_DEVIATION = "CSE07_SUPERVISORY_DEVIATION"

    # Mixed Signal
    COMPOUND_SUSPICIOUS_PATTERN = "COMPOUND_SUSPICIOUS_PATTERN"

    # Legitimate Exception scenario types (for false positive suppression testing)
    MAINTENANCE_WINDOW_EXPLANATION = "MAINTENANCE_WINDOW_EXPLANATION"
    DECOMMISSIONED_ASSET_EXPLANATION = "DECOMMISSIONED_ASSET_EXPLANATION"
    OPERATIONAL_SUPPRESSION_EXPLANATION = "OPERATIONAL_SUPPRESSION_EXPLANATION"
    DATA_EXPORT_INCOMPLETE_EXPLANATION = "DATA_EXPORT_INCOMPLETE_EXPLANATION"

    # Normal
    STANDARD_OPERATIONAL_WORKFLOW = "STANDARD_OPERATIONAL_WORKFLOW"


@dataclass
class GroundTruthScenario:
    scenario_id: str
    scenario_class: ScenarioClass
    scenario_type: ScenarioType
    target_entity_id: str
    target_entity_type: str  # CSE, Asset, Alert, Case, Investigation
    expected_finding_rule: Optional[str]  # e.g., GAP-01, NEG-01, PEER-01
    is_legitimate_exception: bool = False
    exception_reason: Optional[str] = None
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_class": self.scenario_class.value,
            "scenario_type": self.scenario_type.value,
            "target_entity_id": str(self.target_entity_id),
            "target_entity_type": self.target_entity_type,
            "expected_finding_rule": self.expected_finding_rule,
            "is_legitimate_exception": self.is_legitimate_exception,
            "exception_reason": self.exception_reason,
            "description": self.description
        }


@dataclass
class DatasetManifest:
    generator_version: str
    seed: int
    generated_at: str
    record_counts: Dict[str, int]
    scenario_counts: Dict[str, int]
    time_range: Dict[str, str]
    ground_truth_scenarios: List[GroundTruthScenario]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generator_version": self.generator_version,
            "seed": self.seed,
            "generated_at": self.generated_at,
            "record_counts": self.record_counts,
            "scenario_counts": self.scenario_counts,
            "time_range": self.time_range,
            "ground_truth_scenarios": [s.to_dict() for s in self.ground_truth_scenarios]
        }
