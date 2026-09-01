"""Non-Destructive Threat Intelligence Context Enrichment Engine."""
from typing import Dict, Any, Optional
from app.intelligence.models import SecurityEnrichmentContext, MappingType
from app.intelligence.mapper import SATSAThreatMapper
from app.intelligence.cpe_matcher import CPEMatcher


class ThreatEnrichmentEngine:
    """Enriches SAT-SA monitored assets, alerts, and findings with external threat intelligence context."""

    def __init__(
        self,
        nvd_catalog: Optional[Dict[str, Any]] = None,
        kev_catalog: Optional[Dict[str, Any]] = None,
        attack_catalog: Optional[Dict[str, Any]] = None
    ):
        self.nvd_catalog = nvd_catalog or {}
        self.kev_catalog = kev_catalog or {}
        self.attack_catalog = attack_catalog or {}
        self.cpe_matcher = CPEMatcher(self.nvd_catalog)

    def enrich_asset(self, asset_type: str, asset_name: str) -> SecurityEnrichmentContext:
        """Enriches asset with CPE, CVE, CVSS, CISA KEV, and threat group intelligence."""
        return SATSAThreatMapper.map_asset_context(
            asset_type=asset_type,
            asset_name=asset_name,
            nvd_catalog=self.nvd_catalog,
            kev_catalog=self.kev_catalog,
            attack_catalog=self.attack_catalog,
            cpe_matcher=self.cpe_matcher
        )

    def enrich_finding(self, rule_id: str, asset_type: Optional[str] = None) -> SecurityEnrichmentContext:
        """Enriches finding with defensible ATT&CK technique mapping and context."""
        tech_id, map_type, justification, conf = SATSAThreatMapper.map_rule_to_technique(rule_id)
        
        tech_name = "Unknown"
        tactics = []
        if tech_id and self.attack_catalog:
            tech_info = self.attack_catalog.get("techniques", {}).get(tech_id, {})
            tech_name = tech_info.get("name", tech_id)
            tactics = tech_info.get("tactics", [])

        summary = f"Rule {rule_id} mapped to ATT&CK {tech_id} ({tech_name}) via {map_type.value} [Confidence: {conf}]: {justification}"

        return SecurityEnrichmentContext(
            attack_tactics=tactics,
            attack_techniques=[{"id": tech_id, "name": tech_name}] if tech_id else [],
            threat_context_summary=summary,
            threat_score_modifier=5.0 if map_type == MappingType.DIRECT else (2.5 if map_type == MappingType.SUPPORTED_INFERENCE else 0.0),
            provenance_sources=["MITRE_ATTACK_v15", "SAT-SA_THREAT_MAPPER"]
        )
