import enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from app.models import RuleVersion, FindingSeverity
from app.evidence.reconstructor import OperationalWorkflowNode


class EvaluationStatus(str, enum.Enum):
    CONFIRMED = "CONFIRMED"
    FAIL = "FAIL"  # For backwards compatibility with ExecutionGapEngine
    PASS = "PASS"
    SUPPRESSED = "SUPPRESSED"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    UNKNOWN = "UNKNOWN"  # Data incomplete
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"


@dataclass
class RuleEvaluationResult:
    rule_id: str
    rule_version: str
    target_node: Optional[OperationalWorkflowNode] = None
    status: EvaluationStatus = EvaluationStatus.PASS
    applicability: bool = True
    expected_behaviour: str = ""
    observed_behaviour: str = ""
    severity: FindingSeverity = FindingSeverity.MEDIUM
    confidence: float = 1.0
    risk_contribution: float = 0.0
    evidence_refs: List[Dict[str, Any]] = field(default_factory=list)
    explanation: str = ""
    recommendation: str = ""

    # Phase 6 Negative Space structured result fields
    target_entity_id: Optional[str] = None
    target_entity_type: Optional[str] = None
    expectation: Optional[str] = None
    expected_window: Optional[str] = None
    observed_window: Optional[str] = None
    expected_activity: Optional[Any] = None
    observed_activity: Optional[Any] = None
    absence_deviation_measurement: Optional[Any] = None
    baseline: Optional[Dict[str, Any]] = field(default_factory=dict)
    context_checks: Optional[Dict[str, Any]] = field(default_factory=dict)
    data_quality: Optional[Dict[str, Any]] = field(default_factory=dict)

