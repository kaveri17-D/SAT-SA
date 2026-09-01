"""Executive Report Generator."""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from app.reporting.generators.base import BaseReportGenerator
from app.models.enums import ReportType


class ExecutiveReportGenerator(BaseReportGenerator):
    """Generates concise, decision-oriented executive summaries."""

    def generate(self, report_number: str, title: Optional[str] = None) -> Dict[str, Any]:
        findings = self.get_findings()
        risk_scores = self.get_risk_scores()
        assets = self.get_assets()

        # Primary risk score
        primary_risk = risk_scores[0] if risk_scores else None
        overall_score = round(primary_risk.normalized_score if primary_risk else 0.0, 2)
        risk_band = primary_risk.risk_band if primary_risk else "LOW"
        confidence = round(primary_risk.overall_confidence if primary_risk else 1.0, 2)
        breakdown = primary_risk.component_breakdown if primary_risk else {}

        severity_dist = self.get_severity_distribution(findings)
        posture = self.calculate_security_posture(overall_score, severity_dist["CRITICAL"])

        # Top security gaps
        top_gaps = []
        for f in findings[:5]:
            enrichment = self.enricher.enrich_finding(f.rule_id or "UNKNOWN")
            top_gaps.append({
                "finding_id": str(f.id),
                "rule_id": f.rule_id,
                "severity": f.severity.value if hasattr(f.severity, "value") else str(f.severity),
                "supervisory_priority": round(f.supervisory_priority, 2),
                "reason": f.reason,
                "recommendation": f.recommendation,
                "attack_techniques": [t["id"] for t in enrichment.attack_techniques] if enrichment else []
            })

        # KEV & Critical exposures
        kev_exposures = []
        for asset in assets:
            ctx = self.enricher.enrich_asset(asset.asset_type, asset.name)
            if ctx and ctx.is_cisa_kev:
                kev_exposures.append({
                    "asset_name": asset.name,
                    "asset_type": asset.asset_type,
                    "cve_id": ctx.cve_id,
                    "cvss_score": ctx.cvss_base_score,
                    "threat_groups": ctx.threat_groups,
                    "required_action": "Apply vendor security patch immediately per CISA directive."
                })

        # Strategic recommendations
        recommendations = [
            {"priority": "IMMEDIATE_24H", "action": "Remediate active CISA KEV exposed assets and investigate unassigned critical alerts."},
            {"priority": "SHORT_TERM_7D", "action": "Address telemetry silence gaps on high-criticality assets to restore monitoring visibility."},
            {"priority": "MEDIUM_TERM_30D", "action": "Align SOC operational triage thresholds with supervisory peer benchmarks to eliminate excessive triage delays."}
        ]

        report_title = title or f"Executive Cyber Supervisory Assessment Report — {self.cse.name if self.cse else 'Enterprise Portfolio'}"

        summary = {
            "overall_security_posture": posture,
            "overall_risk_score": overall_score,
            "risk_band": risk_band,
            "total_findings": len(findings),
            "critical_findings": severity_dist["CRITICAL"],
            "high_findings": severity_dist["HIGH"],
            "kev_exposures_count": len(kev_exposures),
            "assets_assessed": len(assets)
        }

        content = {
            "report_header": {
                "report_number": report_number,
                "report_type": ReportType.EXECUTIVE.value,
                "title": report_title,
                "assessment_id": str(self.run.id),
                "cse_name": self.cse.name if self.cse else "All Critical Sector Entities",
                "cse_sector": self.cse.sector if self.cse else "MULTI_SECTOR",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "governance_classification": "OFFICIAL / SUPERVISORY ONLY"
            },
            "executive_summary": {
                "narrative": (
                    f"Supervisory assessment of {self.cse.name if self.cse else 'the critical infrastructure portfolio'} "
                    f"identifies an overall security posture of {posture} with a normalized risk score of {overall_score}/100 "
                    f"({risk_band} band). A total of {len(findings)} supervisory findings were detected, including "
                    f"{severity_dist['CRITICAL']} Critical and {severity_dist['HIGH']} High severity operational gaps."
                ),
                "posture": posture,
                "risk_score": overall_score,
                "risk_band": risk_band,
                "confidence": confidence,
                "component_breakdown": breakdown
            },
            "severity_distribution": severity_dist,
            "top_security_gaps": top_gaps,
            "kev_and_critical_exposures": kev_exposures,
            "strategic_recommendations": recommendations,
            "provenance_metadata": {
                "rule_version": self.run.rule_version,
                "model_version": self.run.model_version,
                "data_foundation_version": "1.0.0",
                "air_gap_status": "STRICT_LOCAL_ONLY"
            }
        }

        return {"summary": summary, "content": content}
