"""Supervisory Risk Report Generator."""
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
from app.reporting.generators.base import BaseReportGenerator
from app.models.enums import ReportType


class RiskReportGenerator(BaseReportGenerator):
    """Generates structured 5-component supervisory risk reports."""

    def generate(self, report_number: str, title: Optional[str] = None) -> Dict[str, Any]:
        findings = self.get_findings()
        risk_scores = self.get_risk_scores()
        assets = self.get_assets()

        primary_risk = risk_scores[0] if risk_scores else None
        total_score = round(primary_risk.total_score if primary_risk else 0.0, 2)
        raw_score = round(primary_risk.raw_score if primary_risk else 0.0, 2)
        normalized_score = round(primary_risk.normalized_score if primary_risk else 0.0, 2)
        risk_band = primary_risk.risk_band if primary_risk else "LOW"
        confidence = round(primary_risk.overall_confidence if primary_risk else 1.0, 2)
        components = primary_risk.component_breakdown if primary_risk else {
            "execution_gap": 0.0, "negative_space": 0.0, "peer_deviation": 0.0, "investigation_anomaly": 0.0, "asset_criticality": 0.0
        }

        # Risk distribution by asset
        asset_risk_map = {}
        for a in assets:
            ctx = self.enricher.enrich_asset(a.asset_type, a.name)
            base_risk = 20.0
            if a.criticality.value == "CRITICAL": base_risk += 30.0
            elif a.criticality.value == "HIGH": base_risk += 15.0
            if ctx and ctx.is_cisa_kev: base_risk += 40.0
            asset_risk_map[a.name] = {
                "asset_id": str(a.id),
                "asset_type": a.asset_type,
                "criticality": a.criticality.value if hasattr(a.criticality, "value") else str(a.criticality),
                "calculated_asset_risk": min(round(base_risk, 2), 100.0),
                "is_cisa_kev": ctx.is_cisa_kev if ctx else False,
                "cve_id": ctx.cve_id if ctx else None
            }

        sorted_assets = sorted(asset_risk_map.items(), key=lambda x: x[1]["calculated_asset_risk"], reverse=True)

        report_title = title or f"Supervisory Risk Analysis & Decomposition Report — {self.cse.name if self.cse else 'Enterprise Portfolio'}"

        summary = {
            "overall_risk_score": normalized_score,
            "raw_risk_score": raw_score,
            "risk_band": risk_band,
            "confidence": confidence,
            "highest_risk_component": max(components.items(), key=lambda x: x[1])[0] if components else "NONE",
            "high_risk_assets_count": sum(1 for a in asset_risk_map.values() if a["calculated_asset_risk"] >= 70.0)
        }

        content = {
            "report_header": {
                "report_number": report_number,
                "report_type": ReportType.RISK.value,
                "title": report_title,
                "assessment_id": str(self.run.id),
                "cse_name": self.cse.name if self.cse else "All Critical Sector Entities",
                "generated_at": datetime.now(timezone.utc).isoformat()
            },
            "risk_summary": {
                "normalized_score": normalized_score,
                "raw_score": raw_score,
                "total_score": total_score,
                "risk_band": risk_band,
                "confidence": confidence
            },
            "five_component_decomposition": {
                "R1_execution_gap": {
                    "score": round(components.get("execution_gap", 0.0), 2),
                    "description": "Risk derived from uninvestigated alerts, triage delays, and premature ticket closures."
                },
                "R2_negative_space": {
                    "score": round(components.get("negative_space", 0.0), 2),
                    "description": "Risk derived from sensor silence gaps, targeted logging disablement, and unmonitored assets."
                },
                "R3_peer_deviation": {
                    "score": round(components.get("peer_deviation", 0.0), 2),
                    "description": "Risk derived from anomaly divergence relative to sector cohort baseline."
                },
                "R4_investigation_anomaly": {
                    "score": round(components.get("investigation_anomaly", 0.0), 2),
                    "description": "Risk derived from investigator triage anomalies and suppression patterns."
                },
                "R5_asset_criticality": {
                    "score": round(components.get("asset_criticality", 0.0), 2),
                    "description": "Multiplier derived from high-value target assets and infrastructure criticality ratings."
                }
            },
            "risk_distribution_by_asset": [
                {"asset_name": k, **v} for k, v in sorted_assets
            ],
            "contributing_findings_count": len(findings)
        }

        return {"summary": summary, "content": content}
