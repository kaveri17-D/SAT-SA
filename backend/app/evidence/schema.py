from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone


class EvidenceType(str, Enum):
    DIRECT_RECORD = "DIRECT_RECORD"
    MISSING_EXPECTED_RECORD = "MISSING_EXPECTED_RECORD"
    WORKFLOW_TRANSITION = "WORKFLOW_TRANSITION"
    HISTORICAL_BASELINE = "HISTORICAL_BASELINE"
    PEER_COMPARISON = "PEER_COMPARISON"
    DATA_QUALITY = "DATA_QUALITY"
    CONTEXT_SUPPRESSION = "CONTEXT_SUPPRESSION"
    STATISTICAL_DEVIATION = "STATISTICAL_DEVIATION"


@dataclass
class EvidenceRecordItem:
    evidence_id: str
    evidence_type: str
    source_entity_type: str
    source_record_id: str
    evidence_timestamp: Optional[str]
    description: str
    relevance: str
    payload: Dict[str, Any]
    provenance: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "evidence_type": self.evidence_type,
            "source_entity_type": self.source_entity_type,
            "source_table": self.source_entity_type.lower(),
            "source_record_id": self.source_record_id,
            "evidence_timestamp": self.evidence_timestamp,
            "description": self.description,
            "relevance": self.relevance,
            "payload": self.payload,
            "provenance": self.provenance
        }


@dataclass
class WorkflowDifference:
    expected_sequence: List[str]
    observed_sequence: List[str]
    missing_transitions: List[Dict[str, str]]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "expected_sequence": self.expected_sequence,
            "observed_sequence": self.observed_sequence,
            "missing_transitions": self.missing_transitions
        }


@dataclass
class EvidencePackage:
    finding_id: str
    rule_id: str
    rule_version: str
    engine: str
    cse_id: str
    asset_id: Optional[str]
    severity: str
    supervisory_metrics: Dict[str, float]
    evidence_completeness: float
    is_evidence_complete: bool
    required_evidence_types: List[str]
    present_evidence_types: List[str]
    detection_source: Dict[str, Any]
    expected_behaviour: str
    observed_behaviour: str
    context: Dict[str, Any]
    supporting_records: List[EvidenceRecordItem]
    workflow_difference: Optional[WorkflowDifference]
    baseline_stats: Optional[Dict[str, Any]]
    peer_stats: Optional[Dict[str, Any]]
    data_quality: Dict[str, Any]
    recommendation: str
    provenance: Dict[str, Any]
    assembled_at: str

    def to_dict(self) -> Dict[str, Any]:
        rec_list = [r.to_dict() for r in self.supporting_records]
        return {
            "finding_id": self.finding_id,
            "rule_id": self.rule_id,
            "rule_version": self.rule_version,
            "engine": self.engine,
            "finding_type": self.engine,
            "cse_id": self.cse_id,
            "asset_id": self.asset_id,
            "severity": self.severity,
            "supervisory_metrics": self.supervisory_metrics,
            "evidence_completeness": self.evidence_completeness,
            "is_evidence_complete": self.is_evidence_complete,
            "required_evidence_types": self.required_evidence_types,
            "present_evidence_types": self.present_evidence_types,
            "detection_source": self.detection_source,
            "expected_behaviour": self.expected_behaviour,
            "observed_behaviour": self.observed_behaviour,
            "deviation": f"Expected: {self.expected_behaviour} | Observed: {self.observed_behaviour}",
            "context": self.context,
            "supporting_records": rec_list,
            "records": rec_list,
            "workflow_difference": self.workflow_difference.to_dict() if self.workflow_difference else None,
            "baseline_stats": self.baseline_stats,
            "peer_stats": self.peer_stats,
            "data_quality": self.data_quality,
            "recommendation": self.recommendation,
            "provenance": self.provenance,
            "assembled_at": self.assembled_at
        }
