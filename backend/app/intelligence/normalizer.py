"""Deterministic Threat Intelligence Normalizer."""
import json
from typing import Dict, List, Any
from app.intelligence.models import (
    AttackBundle, KEVRecord, NVDRecord, SecurityEnrichmentContext
)


class ThreatIntelligenceNormalizer:
    """Normalizes heterogeneous threat intelligence datasets into structured indexed catalogs."""

    @staticmethod
    def normalize_attack(bundle: AttackBundle) -> Dict[str, Any]:
        """Normalizes ATT&CK STIX objects into indexed dictionaries."""
        tech_map = {}
        for t in bundle.techniques:
            tech_map[t.id] = {
                "id": t.id,
                "stix_id": t.stix_id,
                "name": t.name,
                "description": t.description,
                "tactics": t.tactics,
                "is_subtechnique": t.is_subtechnique,
                "platforms": t.platforms,
                "data_sources": t.data_sources,
                "detection_strategy": t.detection_strategy,
                "version": t.version
            }

        tactic_map = {}
        for tac in bundle.tactics:
            tactic_map[tac.shortname] = {
                "id": tac.id,
                "stix_id": tac.stix_id,
                "name": tac.name,
                "shortname": tac.shortname,
                "description": tac.description,
                "version": tac.version
            }

        group_map = {}
        for g in bundle.groups:
            group_map[g.id] = {
                "id": g.id,
                "name": g.name,
                "aliases": g.aliases,
                "description": g.description,
                "version": g.version
            }

        software_map = {}
        for s in bundle.software:
            software_map[s.id] = {
                "id": s.id,
                "name": s.name,
                "software_type": s.software_type,
                "platforms": s.platforms,
                "version": s.version
            }

        return {
            "spec_version": bundle.spec_version,
            "techniques": tech_map,
            "tactics": tactic_map,
            "groups": group_map,
            "software": software_map,
            "counts": {
                "tactics": len(tactic_map),
                "techniques": len(tech_map),
                "groups": len(group_map),
                "software": len(software_map),
                "relationships": len(bundle.relationships)
            }
        }

    @staticmethod
    def normalize_kev(records: List[KEVRecord]) -> Dict[str, Any]:
        """Normalizes CISA KEV records into CVE-indexed dictionary."""
        kev_map = {}
        for r in records:
            kev_map[r.cve_id] = {
                "cve_id": r.cve_id,
                "vendor_project": r.vendor_project,
                "product": r.product,
                "vulnerability_name": r.vulnerability_name,
                "date_added": r.date_added,
                "short_description": r.short_description,
                "required_action": r.required_action,
                "known_ransomware_campaign_use": r.known_ransomware_campaign_use,
                "notes": r.notes,
                "due_date": r.due_date
            }
        return {
            "catalog_type": "CISA_KEV",
            "vulnerabilities": kev_map,
            "total_count": len(kev_map)
        }

    @staticmethod
    def normalize_nvd(records: List[NVDRecord]) -> Dict[str, Any]:
        """Normalizes NVD records with CVE index and CPE criteria lookup."""
        nvd_map = {}
        cpe_to_cve = {}

        for r in records:
            nvd_map[r.cve_id] = {
                "cve_id": r.cve_id,
                "description": r.description,
                "published_date": r.published_date,
                "last_modified_date": r.last_modified_date,
                "cvss_v3_base_score": r.cvss_v3_base_score,
                "cvss_v3_severity": r.cvss_v3_severity,
                "cvss_v3_vector": r.cvss_v3_vector,
                "cvss_v2_base_score": r.cvss_v2_base_score,
                "cwe_ids": r.cwe_ids,
                "cpe_match_criteria": r.cpe_match_criteria,
                "references": r.references
            }
            for cpe in r.cpe_match_criteria:
                if cpe not in cpe_to_cve:
                    cpe_to_cve[cpe] = []
                cpe_to_cve[cpe].append(r.cve_id)

        return {
            "feed_type": "NIST_NVD_2.0",
            "vulnerabilities": nvd_map,
            "cpe_index": cpe_to_cve,
            "total_count": len(nvd_map)
        }
