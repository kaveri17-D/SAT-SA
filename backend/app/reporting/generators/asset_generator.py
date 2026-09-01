"""Asset Report Generator."""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from app.reporting.generators.base import BaseReportGenerator
from app.models.enums import ReportType


class AssetReportGenerator(BaseReportGenerator):
    """Generates asset-centric vulnerability and supervisory finding reports."""

    def generate(self, report_number: str, title: Optional[str] = None) -> Dict[str, Any]:
        findings = self.get_findings()
        assets = self.get_assets()

        # Map findings to assets
        findings_by_asset = {}
        for f in findings:
            if f.asset_id:
                aid = str(f.asset_id)
                findings_by_asset.setdefault(aid, []).append(f)

        asset_profiles = []
        for a in assets:
            aid = str(a.id)
            a_findings = findings_by_asset.get(aid, [])
            enrich = self.enricher.enrich_asset(a.asset_type, a.name)

            asset_profiles.append({
                "asset_id": aid,
                "name": a.name,
                "asset_type": a.asset_type,
                "criticality": a.criticality.value if hasattr(a.criticality, "value") else str(a.criticality),
                "status": a.status,
                "findings_count": len(a_findings),
                "vulnerability_context": {
                    "cve_id": enrich.cve_id if enrich else None,
                    "cvss_base_score": enrich.cvss_base_score if enrich else None,
                    "is_cisa_kev": enrich.is_cisa_kev if enrich else False,
                    "threat_groups": enrich.threat_groups if enrich else []
                },
                "findings": [
                    {
                        "finding_id": str(f.id),
                        "rule_id": f.rule_id,
                        "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                        "supervisory_priority": round(f.supervisory_priority, 2),
                        "reason": f.reason
                    }
                    for f in a_findings
                ]
            })

        report_title = title or f"Asset-Centric Supervisory Security Report — {self.cse.name if self.cse else 'Enterprise Portfolio'}"

        summary = {
            "total_assets": len(assets),
            "assets_with_findings": sum(1 for ap in asset_profiles if ap["findings_count"] > 0),
            "critical_assets": sum(1 for a in assets if getattr(a.criticality, "value", str(a.criticality)) == "CRITICAL"),
            "kev_exposed_assets": sum(1 for ap in asset_profiles if ap["vulnerability_context"]["is_cisa_kev"])
        }

        content = {
            "report_header": {
                "report_number": report_number,
                "report_type": ReportType.ASSET.value,
                "title": report_title,
                "assessment_id": str(self.run.id),
                "cse_name": self.cse.name if self.cse else "All Critical Sector Entities",
                "generated_at": datetime.now(timezone.utc).isoformat()
            },
            "asset_inventory": asset_profiles
        }

        return {"summary": summary, "content": content}
