"""SAT-SA Cyber Threat Intelligence Domain Models."""
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
from datetime import datetime


class MappingType(str, Enum):
    DIRECT = "DIRECT"
    SUPPORTED_INFERENCE = "SUPPORTED_INFERENCE"
    UNMAPPED = "UNMAPPED"


@dataclass
class AttackTactic:
    id: str
    stix_id: str
    name: str
    shortname: str
    description: str
    external_references: List[Dict[str, str]] = field(default_factory=list)
    version: str = "1.0"


@dataclass
class AttackTechnique:
    id: str
    stix_id: str
    name: str
    description: str
    tactics: List[str] = field(default_factory=list)
    is_subtechnique: bool = False
    parent_technique_id: Optional[str] = None
    platforms: List[str] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    detection_strategy: Optional[str] = None
    version: str = "1.0"


@dataclass
class AttackGroup:
    id: str
    stix_id: str
    name: str
    aliases: List[str] = field(default_factory=list)
    description: str = ""
    techniques_used: List[str] = field(default_factory=list)
    version: str = "1.0"


@dataclass
class AttackSoftware:
    id: str
    stix_id: str
    name: str
    software_type: str = "tool"
    platforms: List[str] = field(default_factory=list)
    techniques_used: List[str] = field(default_factory=list)
    version: str = "1.0"


@dataclass
class AttackMitigation:
    id: str
    stix_id: str
    name: str
    description: str = ""
    techniques_mitigated: List[str] = field(default_factory=list)
    version: str = "1.0"


@dataclass
class AttackRelationship:
    id: str
    source_ref: str
    target_ref: str
    relationship_type: str
    description: str = ""


@dataclass
class AttackBundle:
    tactics: List[AttackTactic] = field(default_factory=list)
    techniques: List[AttackTechnique] = field(default_factory=list)
    groups: List[AttackGroup] = field(default_factory=list)
    software: List[AttackSoftware] = field(default_factory=list)
    mitigations: List[AttackMitigation] = field(default_factory=list)
    relationships: List[AttackRelationship] = field(default_factory=list)
    spec_version: str = "2.1"


@dataclass
class KEVRecord:
    cve_id: str
    vendor_project: str
    product: str
    vulnerability_name: str
    date_added: str
    short_description: str
    required_action: str
    known_ransomware_campaign_use: str
    notes: str = ""
    due_date: Optional[str] = None


@dataclass
class NVDRecord:
    cve_id: str
    description: str
    published_date: str
    last_modified_date: str
    cvss_v3_base_score: Optional[float] = None
    cvss_v3_severity: Optional[str] = None
    cvss_v3_vector: Optional[str] = None
    cvss_v2_base_score: Optional[float] = None
    cwe_ids: List[str] = field(default_factory=list)
    cpe_match_criteria: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)


@dataclass
class SecurityEnrichmentContext:
    cve_id: Optional[str] = None
    cpe_uri: Optional[str] = None
    cvss_base_score: Optional[float] = None
    cvss_severity: Optional[str] = None
    is_cisa_kev: bool = False
    kev_ransomware_use: Optional[str] = None
    attack_tactics: List[str] = field(default_factory=list)
    attack_techniques: List[Dict[str, str]] = field(default_factory=list)
    threat_groups: List[str] = field(default_factory=list)
    threat_software: List[str] = field(default_factory=list)
    threat_context_summary: str = ""
    threat_score_modifier: float = 0.0
    provenance_sources: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "cve_id": self.cve_id,
            "cpe_uri": self.cpe_uri,
            "cvss_base_score": self.cvss_base_score,
            "cvss_severity": self.cvss_severity,
            "is_cisa_kev": self.is_cisa_kev,
            "kev_ransomware_use": self.kev_ransomware_use,
            "attack_tactics": self.attack_tactics,
            "attack_techniques": self.attack_techniques,
            "threat_groups": self.threat_groups,
            "threat_software": self.threat_software,
            "threat_context_summary": self.threat_context_summary,
            "threat_score_modifier": self.threat_score_modifier,
            "provenance_sources": self.provenance_sources,
        }


@dataclass
class DataQualityReport:
    source_name: str
    total_records: int
    valid_records: int
    rejected_records: int
    duplicate_records: int
    malformed_ids: int
    missing_required_fields: int
    deprecated_or_revoked: int = 0
    unmapped_entities: int = 0
    conflicting_records: int = 0
    issues: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_name": self.source_name,
            "total_records": self.total_records,
            "valid_records": self.valid_records,
            "rejected_records": self.rejected_records,
            "duplicate_records": self.duplicate_records,
            "malformed_ids": self.malformed_ids,
            "missing_required_fields": self.missing_required_fields,
            "deprecated_or_revoked": self.deprecated_or_revoked,
            "unmapped_entities": self.unmapped_entities,
            "conflicting_records": self.conflicting_records,
            "issues": self.issues,
        }


@dataclass
class ScenarioDefinition:
    scenario_id: str
    name: str
    description: str
    category: str
    source_datasets: List[str]
    input_entities: Dict[str, Any]
    expected_condition: str
    expected_detection_status: str
    expected_threat_context: Dict[str, Any]
    ground_truth_label: str
    provenance: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "source_datasets": self.source_datasets,
            "input_entities": self.input_entities,
            "expected_condition": self.expected_condition,
            "expected_detection_status": self.expected_detection_status,
            "expected_threat_context": self.expected_threat_context,
            "ground_truth_label": self.ground_truth_label,
            "provenance": self.provenance,
        }


@dataclass
class GroundTruthEntry:
    scenario_id: str
    entity_type: str
    target_id: str
    is_anomalous: bool
    expected_rules: List[str]
    expected_severity: str
    expected_cve: Optional[str]
    expected_kev: bool
    expected_techniques: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "entity_type": self.entity_type,
            "target_id": self.target_id,
            "is_anomalous": self.is_anomalous,
            "expected_rules": self.expected_rules,
            "expected_severity": self.expected_severity,
            "expected_cve": self.expected_cve,
            "expected_kev": self.expected_kev,
            "expected_techniques": self.expected_techniques,
        }
