import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session

from app.models import RiskScore, Finding, Evidence, AnalysisRun, CSE, Asset, FindingSeverity, FindingStatus, AssetCriticality
from app.core.logging import logger


COMPONENT_CAPS = {
    "execution_gap": 30.0,
    "negative_space": 25.0,
    "peer_deviation": 20.0,
    "investigation_anomaly": 15.0,
    "asset_criticality": 10.0
}

RISK_BAND_THRESHOLDS = [
    (0.0, 24.99, "LOW"),
    (25.0, 49.99, "MODERATE"),
    (50.0, 74.99, "HIGH"),
    (75.0, 100.0, "CRITICAL")
]


class SupervisoryRiskEngine:
    """Independent service converting findings and canonical evidence into decomposable CSE-level supervisory risk scores."""

    @staticmethod
    def classify_risk_band(score: float) -> str:
        """Map normalized risk score to configurable risk bands."""
        clamped_score = max(0.0, min(100.0, score))
        for low, high, band in RISK_BAND_THRESHOLDS:
            if low <= clamped_score <= high:
                return band
        return "CRITICAL" if clamped_score >= 75.0 else "LOW"

    @staticmethod
    def compute_cse_risk_score(db: Session, cse_id: uuid.UUID, analysis_run_id: uuid.UUID) -> RiskScore:
        """Compute transparent, decomposable CSE risk score from findings and canonical evidence."""
        cse = db.query(CSE).filter(CSE.id == cse_id).first()
        if not cse:
            raise ValueError(f"CSE '{cse_id}' not found.")

        analysis_run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_run_id).first()
        rule_ver = analysis_run.rule_version if analysis_run else "1.0.0"
        model_ver = analysis_run.model_version if analysis_run else "1.0.0"

        # 1. Fetch all findings for this CSE in this AnalysisRun (strictly isolated by cse_id & analysis_run_id)
        findings = db.query(Finding).filter(
            Finding.cse_id == cse_id,
            Finding.analysis_run_id == analysis_run_id
        ).all()

        # 2. Filter out SUPPRESSED / DISMISSED / legitimate exception findings
        active_findings = [
            f for f in findings 
            if f.status not in (FindingStatus.SUPPRESSED, FindingStatus.DISMISSED) 
            and "SUPPRESSED" not in str(f.reason).upper()
            and "SUPPRESSED" not in str(f.observed_behaviour).upper()
        ]

        # 3. Deduplicate findings by rule component & calculate contributions
        component_scores: Dict[str, float] = {
            "execution_gap": 0.0,
            "negative_space": 0.0,
            "peer_deviation": 0.0,
            "investigation_anomaly": 0.0,
            "asset_criticality": 0.0
        }

        contributing_finding_records: List[Dict[str, Any]] = []
        contributing_finding_ids: List[str] = []
        evidence_refs_collected: List[Dict[str, Any]] = []
        confidence_values: List[float] = []
        qualifications_applied: List[str] = []

        # Process active findings
        for f in active_findings:
            rule_id = f.rule_id or ""
            base_contrib = 0.0
            component_cat = ""

            if rule_id.startswith("GAP"):
                if rule_id in ("GAP-02", "GAP-04", "GAP-05"):
                    component_cat = "investigation_anomaly"
                    base_contrib = 15.0
                else:
                    component_cat = "execution_gap"
                    if f.severity == FindingSeverity.CRITICAL:
                        base_contrib = 30.0
                    elif f.severity == FindingSeverity.HIGH:
                        base_contrib = 25.0
                    elif f.severity == FindingSeverity.MEDIUM:
                        base_contrib = 18.0
                    else:
                        base_contrib = 10.0
            elif rule_id == "NEG-04":
                component_cat = "peer_deviation"
                base_contrib = 20.0
            elif rule_id.startswith("NEG"):
                component_cat = "negative_space"
                if f.severity == FindingSeverity.CRITICAL:
                    base_contrib = 25.0
                elif f.severity == FindingSeverity.HIGH:
                    base_contrib = 20.0
                elif f.severity == FindingSeverity.MEDIUM:
                    base_contrib = 15.0
                else:
                    base_contrib = 8.0

            if component_cat:
                # Explicit, deterministic confidence adjustment policy
                conf = max(0.0, min(1.0, f.confidence))
                confidence_values.append(conf)

                if conf < 0.70:
                    effective_contrib = round(base_contrib * max(0.50, conf), 2)
                    qualifications_applied.append(
                        f"Finding '{f.id}' ({rule_id}) risk contribution scaled from {base_contrib:.1f} to {effective_contrib:.1f} due to low confidence ({conf:.2f})."
                    )
                else:
                    effective_contrib = base_contrib

                # Apply Deduplication Policy: take max contribution per component category
                if effective_contrib > component_scores[component_cat]:
                    component_scores[component_cat] = effective_contrib

                contributing_finding_ids.append(str(f.id))
                contributing_finding_records.append({
                    "finding_id": str(f.id),
                    "rule_id": rule_id,
                    "component_category": component_cat,
                    "base_contribution": base_contrib,
                    "effective_contribution": effective_contrib,
                    "severity": f.severity.value,
                    "confidence": conf,
                    "reason": f.reason
                })

                if f.evidence_refs:
                    evidence_refs_collected.extend(f.evidence_refs)

        # 4. Evaluate Asset Criticality Component (+10 for CRITICAL asset, +6 for HIGH asset)
        cse_assets = db.query(Asset).filter(Asset.cse_id == cse_id, Asset.status == "ACTIVE").all()
        has_critical = any(a.criticality == AssetCriticality.CRITICAL for a in cse_assets)
        has_high = any(a.criticality == AssetCriticality.HIGH for a in cse_assets)

        if has_critical:
            component_scores["asset_criticality"] = 10.0
        elif has_high:
            component_scores["asset_criticality"] = 6.0

        # Cap each component score at its documented max cap
        for cat, cap in COMPONENT_CAPS.items():
            component_scores[cat] = min(cap, max(0.0, component_scores[cat]))

        # 5. Compute Raw & Normalized Aggregate Risk Score
        raw_score = sum(component_scores.values())
        normalized_score = round(max(0.0, min(100.0, raw_score)), 2)
        risk_band = SupervisoryRiskEngine.classify_risk_band(normalized_score)
        overall_confidence = round(sum(confidence_values) / len(confidence_values), 4) if confidence_values else 1.0

        # 6. Generate Structured "Why This Score?" Explanation directly from calculation state
        explanation_json = {
            "title": f"CSE '{cse.name}' Supervisory Risk: {normalized_score:.1f} / 100 — {risk_band}",
            "cse_id": str(cse.id),
            "cse_name": cse.name,
            "raw_score": raw_score,
            "normalized_score": normalized_score,
            "risk_band": risk_band,
            "overall_confidence": overall_confidence,
            "component_breakdown": component_scores,
            "component_caps": COMPONENT_CAPS,
            "contributing_findings_count": len(contributing_finding_records),
            "contributing_findings": contributing_finding_records,
            "evidence_references": evidence_refs_collected[:10],  # Top evidence refs
            "confidence_qualifications": qualifications_applied,
            "calculated_at": datetime.now(timezone.utc).isoformat()
        }

        provenance_json = {
            "dataset_import_id": str(analysis_run.dataset_import_id) if analysis_run else None,
            "analysis_run_id": str(analysis_run_id),
            "rule_version": rule_ver,
            "model_version": model_ver,
            "engine": "SupervisoryRiskEngine"
        }

        # 7. Idempotent Storage: Update existing record or create new
        existing_risk = db.query(RiskScore).filter(
            RiskScore.cse_id == cse_id,
            RiskScore.analysis_run_id == analysis_run_id
        ).first()

        if existing_risk:
            existing_risk.computed_at = datetime.now(timezone.utc)
            existing_risk.total_score = normalized_score
            existing_risk.raw_score = raw_score
            existing_risk.normalized_score = normalized_score
            existing_risk.risk_band = risk_band
            existing_risk.overall_confidence = overall_confidence
            existing_risk.component_breakdown = component_scores
            existing_risk.contributing_finding_ids = contributing_finding_ids
            existing_risk.explanation_json = explanation_json
            existing_risk.provenance_json = provenance_json
            existing_risk.rule_version = rule_ver
            existing_risk.model_version = model_ver
            db.commit()
            db.refresh(existing_risk)
            return existing_risk
        else:
            risk_record = RiskScore(
                id=uuid.uuid4(),
                cse_id=cse_id,
                analysis_run_id=analysis_run_id,
                computed_at=datetime.now(timezone.utc),
                total_score=normalized_score,
                raw_score=raw_score,
                normalized_score=normalized_score,
                risk_band=risk_band,
                overall_confidence=overall_confidence,
                component_breakdown=component_scores,
                contributing_finding_ids=contributing_finding_ids,
                explanation_json=explanation_json,
                provenance_json=provenance_json,
                rule_version=rule_ver,
                model_version=model_ver
            )
            db.add(risk_record)
            db.commit()
            db.refresh(risk_record)
            return risk_record

    @staticmethod
    def run_analysis(db: Session, analysis_run_id: uuid.UUID) -> List[RiskScore]:
        """Compute supervisory risk scores across all CSEs for an AnalysisRun."""
        start_time = time.time()
        cses = db.query(CSE).all()
        risk_scores: List[RiskScore] = []

        for cse in cses:
            rs = SupervisoryRiskEngine.compute_cse_risk_score(db, cse.id, analysis_run_id)
            risk_scores.append(rs)

        duration = round(time.time() - start_time, 4)
        throughput_cses = round(len(cses) / duration, 2) if duration > 0 else 0.0
        logger.info(f"SupervisoryRiskEngine processed {len(cses)} CSEs in {duration}s ({throughput_cses} CSEs/sec).")
        return risk_scores

    compute_supervisory_risk = run_analysis

