"""Vulnerability & Threat Intelligence Report Generator."""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from app.reporting.generators.base import BaseReportGenerator
from app.models.enums import ReportType


class ThreatIntelligenceReportGenerator(BaseReportGenerator):
    """Generates vulnerability and threat-intelligence backed reports integrating Phase 13 catalogs."""

    def generate(self, report_number: str, title: Optional[str] = None) -> Dict[str, Any]:
        findings = self.get_findings()
        assets = self.get_assets()

        # Compile CVE inventory
        cve_inventory = {}
        for a in assets:
            ctx = self.enricher.enrich_asset(a.asset_type, a.name)
            if ctx and ctx.cve_id and ctx.cve_id not in cve_inventory:
                cve_inventory[ctx.cve_id] = {
                    "cve_id": ctx.cve_id,
                    "cvss_base_score": ctx.cvss_base_score,
                    "is_cisa_kev": ctx.is_cisa_kev,
                    "threat_groups": ctx.threat_groups,
                    "affected_asset_types": [a.asset_type],
                    "sample_asset": a.name
                }
            elif ctx and ctx.cve_id:
                if a.asset_type not in cve_inventory[ctx.cve_id]["affected_asset_types"]:
                    cve_inventory[ctx.cve_id]["affected_asset_types"].append(a.asset_type)

        # ATT&CK Techniques mapping
        attack_mappings = []
        seen_techs = set()
        for f in findings:
            enrich = self.enricher.enrich_finding(f.rule_id or "UNKNOWN")
            if enrich:
                for tech in enrich.attack_techniques:
                    if tech["id"] not in seen_techs:
                        seen_techs.add(tech["id"])
                        attack_mappings.append({
                            "technique_id": tech["id"],
                            "name": tech["name"],
                            "tactics": enrich.attack_tactics if enrich and enrich.attack_tactics else [],
                            "associated_rule": f.rule_id,
                            "mapping_type": "DIRECT" if tech["id"].startswith("T1562.002") or tech["id"].startswith("T1070.001") else "SUPPORTED_INFERENCE"
                        })

        report_title = title or f"Vulnerability & Cyber Threat Intelligence Report — {self.cse.name if self.cse else 'Enterprise Portfolio'}"

        summary = {
            "total_cves_mapped": len(cve_inventory),
            "cisa_kev_cves": sum(1 for c in cve_inventory.values() if c["is_cisa_kev"]),
            "attack_techniques_identified": len(attack_mappings),
            "threat_groups_associated": len(set(g for c in cve_inventory.values() for g in c["threat_groups"]))
        }

        content = {
            "report_header": {
                "report_number": report_number,
                "report_type": ReportType.VULNERABILITY_THREAT_INTEL.value,
                "title": report_title,
                "assessment_id": str(self.run.id),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "data_foundation_version": "1.0.0"
            },
            "cve_vulnerability_inventory": list(cve_inventory.values()),
            "mitre_attack_matrix_coverage": attack_mappings,
            "provenance_and_authoritative_sources": [
                {"source": "NIST National Vulnerability Database (NVD 2.0)", "version": "2.0", "status": "VALIDATED"},
                {"source": "CISA Known Exploited Vulnerabilities Catalog", "version": "2026.08.31", "status": "VALIDATED"},
                {"source": "MITRE ATT&CK Enterprise STIX 2.1", "version": "v15.0", "status": "VALIDATED"}
            ]
        }

        return {"summary": summary, "content": content}
