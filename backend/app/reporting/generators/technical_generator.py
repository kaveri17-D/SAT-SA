"""Technical Report Generator."""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from app.reporting.generators.base import BaseReportGenerator
from app.models.enums import ReportType


class TechnicalReportGenerator(BaseReportGenerator):
    """Generates detailed technical reports for security and SOC teams."""

    def generate(self, report_number: str, title: Optional[str] = None) -> Dict[str, Any]:
        findings = self.get_findings()
        assets = self.get_assets()
        severity_dist = self.get_severity_distribution(findings)

        detailed_findings = []
        for f in findings:
            enrichment = self.enricher.enrich_finding(f.rule_id or "UNKNOWN")
            asset = f.asset
            asset_enrich = self.enricher.enrich_asset(asset.asset_type, asset.name) if asset else None

            ev_refs = [
                {
                    "evidence_id": str(ev.id),
                    "evidence_type": ev.evidence_type,
                    "source_table": ev.source_table,
                    "source_record_id": ev.source_record_id,
                    "relevance": ev.relevance,
                    "description": ev.description
                }
                for ev in f.evidence_records
            ]

            detailed_findings.append({
                "finding_id": str(f.id),
                "rule_id": f.rule_id,
                "rule_version": f.rule_version,
                "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                "status": f.status.value if hasattr(f.status, "value") else str(f.status),
                "anomaly_score": round(f.anomaly_score, 4),
                "confidence": round(f.confidence, 4),
                "supervisory_priority": round(f.supervisory_priority, 4),
                "evidence_completeness": round(f.evidence_completeness, 2),
                "reason": f.reason,
                "expected_behaviour": f.expected_behaviour,
                "observed_behaviour": f.observed_behaviour,
                "recommendation": f.recommendation,
                "asset": {
                    "asset_id": str(asset.id) if asset else None,
                    "name": asset.name if asset else "UNSPECIFIED",
                    "asset_type": asset.asset_type if asset else "UNKNOWN",
                    "criticality": asset.criticality.value if asset and hasattr(asset.criticality, "value") else "MEDIUM"
                } if asset else None,
                "threat_intelligence": {
                    "attack_techniques": enrichment.attack_techniques if enrichment else [],
                    "cve_id": asset_enrich.cve_id if asset_enrich else None,
                    "cvss_base_score": asset_enrich.cvss_base_score if asset_enrich else None,
                    "is_cisa_kev": asset_enrich.is_cisa_kev if asset_enrich else False,
                    "threat_groups": asset_enrich.threat_groups if asset_enrich else []
                },
                "evidence_records": ev_refs
            })

        report_title = title or f"Technical Cyber Supervisory Assessment Report — {self.cse.name if self.cse else 'Enterprise Portfolio'}"

        summary = {
            "total_findings": len(detailed_findings),
            "critical_findings": severity_dist["CRITICAL"],
            "high_findings": severity_dist["HIGH"],
            "medium_findings": severity_dist["MEDIUM"],
            "low_findings": severity_dist["LOW"],
            "assets_evaluated": len(assets),
            "total_evidence_records": sum(len(f["evidence_records"]) for f in detailed_findings)
        }

        content = {
            "report_header": {
                "report_number": report_number,
                "report_type": ReportType.TECHNICAL.value,
                "title": report_title,
                "assessment_id": str(self.run.id),
                "cse_name": self.cse.name if self.cse else "All Critical Sector Entities",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "schema_version": "1.0.0"
            },
            "scope_and_infrastructure": {
                "cse_id": str(self.cse.id) if self.cse else None,
                "cse_name": self.cse.name if self.cse else "Enterprise",
                "sector": self.cse.sector if self.cse else "MULTI_SECTOR",
                "records_processed": self.run.records_processed,
                "findings_generated": self.run.findings_generated,
                "rule_version": self.run.rule_version,
                "model_version": self.run.model_version
            },
            "severity_distribution": severity_dist,
            "detailed_findings": detailed_findings
        }

        return {"summary": summary, "content": content}
