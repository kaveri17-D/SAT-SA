import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.models import (
    ReviewQueueItem, Finding, RiskScore, Asset, CSE, AnalysisRun, AuditLog,
    FindingSeverity, FindingStatus, QueueItemStatus, AssetCriticality
)
from app.core.logging import logger

FACTOR_WEIGHTS = {
    "risk_significance": 0.25,
    "finding_severity": 0.20,
    "asset_criticality": 0.15,
    "evidence_completeness": 0.15,
    "evidence_confidence": 0.10,
    "novelty": 0.05,
    "peer_deviation": 0.05,
    "review_urgency": 0.05
}

PRIORITY_BAND_THRESHOLDS = [
    (75.0, 100.0, "CRITICAL"),
    (50.0, 74.99, "HIGH"),
    (25.0, 49.99, "MEDIUM"),
    (0.0, 24.99, "LOW")
]


class ReviewPrioritizationEngine:
    """Independent service converting evidence-backed findings into a ranked, diverse, explainable supervisory review queue."""

    @staticmethod
    def classify_priority_band(score: float) -> str:
        """Map prioritization score to configurable priority bands."""
        clamped = max(0.0, min(100.0, score))
        for low, high, band in PRIORITY_BAND_THRESHOLDS:
            if low <= clamped <= high:
                return band
        return "CRITICAL" if clamped >= 75.0 else "LOW"

    @staticmethod
    def compute_candidate_score(
        finding: Finding,
        cse_risk_score: float,
        asset: Optional[Asset]
    ) -> Tuple[float, Dict[str, float], List[str]]:
        """Compute decomposable 8-factor prioritization score (0..100) and rationale factors."""
        # 1. Risk Significance (25%): Max of CSE normalized risk score or finding risk score
        f_risk = getattr(finding, "risk_score", 0.0) or 0.0
        risk_sig_val = max(0.0, min(100.0, max(cse_risk_score, f_risk)))

        # 2. Finding Severity (20%)
        if finding.severity == FindingSeverity.CRITICAL:
            sev_val = 100.0
        elif finding.severity == FindingSeverity.HIGH:
            sev_val = 80.0
        elif finding.severity == FindingSeverity.MEDIUM:
            sev_val = 50.0
        else:
            sev_val = 25.0

        # 3. Asset Criticality (15%)
        if asset:
            if asset.criticality == AssetCriticality.CRITICAL:
                asset_crit_val = 100.0
            elif asset.criticality == AssetCriticality.HIGH:
                asset_crit_val = 70.0
            elif asset.criticality == AssetCriticality.MEDIUM:
                asset_crit_val = 40.0
            else:
                asset_crit_val = 20.0
        else:
            asset_crit_val = 20.0

        # 4. Evidence Completeness (15%)
        ev_comp_val = max(0.0, min(100.0, getattr(finding, "evidence_completeness", 100.0) or 100.0))

        # 5. Evidence Confidence (10%)
        conf_val = max(0.0, min(100.0, (finding.confidence or 1.0) * 100.0))

        # 6. Novelty (5%): NEW status yields 100.0, else 40.0
        novelty_val = 100.0 if finding.status == FindingStatus.NEW else 40.0

        # 7. Peer Deviation (5%): NEG-04 rule yields 100.0
        peer_dev_val = 100.0 if (finding.rule_id and "NEG-04" in finding.rule_id) else 0.0

        # 8. Review Urgency (5%): Based on anomaly score magnitude or age
        urgency_val = max(0.0, min(100.0, (finding.anomaly_score or 0.5) * 100.0))

        factors = {
            "risk_significance": round(risk_sig_val, 2),
            "finding_severity": round(sev_val, 2),
            "asset_criticality": round(asset_crit_val, 2),
            "evidence_completeness": round(ev_comp_val, 2),
            "evidence_confidence": round(conf_val, 2),
            "novelty": round(novelty_val, 2),
            "peer_deviation": round(peer_dev_val, 2),
            "review_urgency": round(urgency_val, 2)
        }

        # Weighted Sum
        raw_priority = sum(factors[k] * FACTOR_WEIGHTS[k] for k in FACTOR_WEIGHTS)
        qualifications: List[str] = []

        # Uncertainty Policy: Low evidence completeness (<40%) incurs -15.0 penalty
        if ev_comp_val < 40.0:
            raw_priority = max(0.0, raw_priority - 15.0)
            qualifications.append(f"Prioritization score penalized by -15.0 due to low evidence completeness ({ev_comp_val:.1f}%).")

        final_priority = round(max(0.0, min(100.0, raw_priority)), 2)
        return final_priority, factors, qualifications

    @staticmethod
    def generate_review_queue(
        db: Session,
        analysis_run_id: uuid.UUID,
        max_per_cse: int = 2,
        max_per_category: int = 3,
        target_queue_size: int = 10
    ) -> Tuple[List[ReviewQueueItem], Dict[str, Any]]:
        """Generate a ranked, diverse, explainable supervisory review queue using 2-pass algorithm."""
        start_time = time.time()
        analysis_run = db.query(AnalysisRun).filter(AnalysisRun.id == analysis_run_id).first()
        if not analysis_run:
            raise ValueError(f"AnalysisRun '{analysis_run_id}' not found.")

        # 1. Fetch all findings for analysis run (Excluding SUPPRESSED and DISMISSED)
        findings = db.query(Finding).filter(
            Finding.analysis_run_id == analysis_run_id,
            Finding.status.notin_([FindingStatus.SUPPRESSED, FindingStatus.DISMISSED])
        ).all()

        # Fetch RiskScores for CSE risk lookup
        risk_scores = db.query(RiskScore).filter(RiskScore.analysis_run_id == analysis_run_id).all()
        risk_map = {rs.cse_id: rs.normalized_score for rs in risk_scores}

        # Fetch Assets for asset criticality lookup
        assets = db.query(Asset).all()
        asset_map = {a.id: a for a in assets}

        # 2. Score candidates & prepare for deterministic sorting
        scored_candidates: List[Dict[str, Any]] = []

        for f in findings:
            cse_risk = risk_map.get(f.cse_id, 0.0)
            asset = asset_map.get(f.asset_id)
            priority_score, factors, qual_notes = ReviewPrioritizationEngine.compute_candidate_score(f, cse_risk, asset)

            rule_cat = f.rule_id.split("-")[0] if (f.rule_id and "-" in f.rule_id) else "GENERAL"

            scored_candidates.append({
                "finding": f,
                "cse_id": f.cse_id,
                "asset": asset,
                "rule_category": rule_cat,
                "priority_score": priority_score,
                "risk_score": cse_risk,
                "confidence": f.confidence or 1.0,
                "created_at": f.created_at or datetime.now(timezone.utc),
                "factors": factors,
                "qualifications": qual_notes
            })

        # Deterministic Sort Key: (-priority_score, -risk_score, -confidence, -created_at, finding_id)
        scored_candidates.sort(
            key=lambda c: (
                -c["priority_score"],
                -c["risk_score"],
                -c["confidence"],
                -c["created_at"].timestamp(),
                str(c["finding"].id)
            )
        )

        # 3. Two-Pass Diversity Algorithm
        selected_candidates: List[Dict[str, Any]] = []
        pass1_selected: List[Dict[str, Any]] = []
        pass2_selected: List[Dict[str, Any]] = []
        excluded_by_diversity: List[Dict[str, Any]] = []

        cse_counts: Dict[uuid.UUID, int] = {}
        category_counts: Dict[str, int] = {}

        # PASS 1: Diversity Selection
        for cand in scored_candidates:
            cid = cand["cse_id"]
            cat = cand["rule_category"]
            c_count = cse_counts.get(cid, 0)
            cat_count = category_counts.get(cat, 0)

            if c_count < max_per_cse and cat_count < max_per_category:
                cand["diversity_note"] = "Selected in Pass 1 (Primary Diversity Pass)"
                pass1_selected.append(cand)
                cse_counts[cid] = c_count + 1
                category_counts[cat] = cat_count + 1
            else:
                excluded_by_diversity.append(cand)

        # PASS 2: Systemic Concentration Fallback (Coverage protection)
        if len(pass1_selected) < target_queue_size and excluded_by_diversity:
            needed = target_queue_size - len(pass1_selected)
            for cand in excluded_by_diversity[:needed]:
                cand["diversity_note"] = "Selected in Pass 2 (Systemic Concentration Fallback - High Risk Coverage)"
                pass2_selected.append(cand)
                cse_counts[cand["cse_id"]] = cse_counts.get(cand["cse_id"], 0) + 1
                category_counts[cand["rule_category"]] = category_counts.get(cand["rule_category"], 0) + 1

        selected_candidates = pass1_selected + pass2_selected

        # Re-sort selected candidates deterministically to maintain strict rank order
        selected_candidates.sort(
            key=lambda c: (
                -c["priority_score"],
                -c["risk_score"],
                -c["confidence"],
                -c["created_at"].timestamp(),
                str(c["finding"].id)
            )
        )

        # 4. Clear existing queue items for this AnalysisRun to ensure idempotency
        db.query(ReviewQueueItem).filter(ReviewQueueItem.analysis_run_id == analysis_run_id).delete()
        db.commit()

        # 5. Persist ReviewQueueItem records
        queue_records: List[ReviewQueueItem] = []
        rule_ver = analysis_run.rule_version or "1.0.0"
        model_ver = analysis_run.model_version or "1.0.0"

        for rank_idx, cand in enumerate(selected_candidates, start=1):
            f = cand["finding"]
            score = cand["priority_score"]
            band = ReviewPrioritizationEngine.classify_priority_band(score)

            rationale = (
                f"Rank #{rank_idx} Review Priority {score:.1f}/100 ({band}). "
                f"Driven by Risk Significance ({cand['factors']['risk_significance']:.1f}), "
                f"Finding Severity ({cand['factors']['finding_severity']:.1f}), "
                f"Asset Criticality ({cand['factors']['asset_criticality']:.1f}), and Evidence Completeness ({cand['factors']['evidence_completeness']:.1f}%)."
            )

            explanation_json = {
                "rank": rank_idx,
                "priority_score": score,
                "priority_band": band,
                "risk_score": cand["risk_score"],
                "confidence": cand["confidence"],
                "evidence_completeness": cand["factors"]["evidence_completeness"],
                "severity": f.severity.value,
                "asset_criticality": cand["factors"]["asset_criticality"],
                "contributing_factors": cand["factors"],
                "factor_weights": FACTOR_WEIGHTS,
                "qualifications": cand["qualifications"],
                "diversity_note": cand["diversity_note"],
                "calculated_at": datetime.now(timezone.utc).isoformat()
            }

            provenance_json = {
                "analysis_run_id": str(analysis_run_id),
                "finding_id": str(f.id),
                "cse_id": str(f.cse_id),
                "rule_version": rule_ver,
                "model_version": model_ver,
                "engine": "ReviewPrioritizationEngine"
            }

            # Find matching RiskScore ID if present
            matching_rs = db.query(RiskScore).filter(RiskScore.cse_id == f.cse_id, RiskScore.analysis_run_id == analysis_run_id).first()

            item = ReviewQueueItem(
                id=uuid.uuid4(),
                analysis_run_id=analysis_run_id,
                finding_id=f.id,
                cse_id=f.cse_id,
                risk_score_id=matching_rs.id if matching_rs else None,
                priority_score=score,
                rank=rank_idx,
                priority_band=band,
                rationale=rationale,
                contributing_factors=cand["factors"],
                explanation_json=explanation_json,
                diversity_notes=cand["diversity_note"],
                status=QueueItemStatus.NEW,
                provenance_json=provenance_json
            )
            queue_records.append(item)

        db.add_all(queue_records)
        db.commit()

        # 6. Diversity Statistics & Metrics Report
        duration = round(time.time() - start_time, 4)
        systemic_concentration_detected = any(cnt >= 3 for cnt in cse_counts.values())

        metrics = {
            "candidates_processed": len(findings),
            "queue_items_generated": len(queue_records),
            "candidates_excluded_by_diversity": len(excluded_by_diversity) - len(pass2_selected),
            "candidates_reintroduced_by_fallback": len(pass2_selected),
            "systemic_concentration_detected": systemic_concentration_detected,
            "cse_diversity_count": len(cse_counts),
            "category_diversity_count": len(category_counts),
            "execution_duration_seconds": duration,
            "throughput_candidates_per_sec": round(len(findings) / duration, 2) if duration > 0 else 0.0
        }

        logger.info(
            f"ReviewPrioritizationEngine generated {len(queue_records)} queue items from {len(findings)} findings in {duration}s "
            f"({metrics['throughput_candidates_per_sec']} candidates/sec). CSE diversity: {metrics['cse_diversity_count']}."
        )

        return queue_records, metrics

    @staticmethod
    def update_item_status(
        db: Session,
        queue_item_id: uuid.UUID,
        new_status: QueueItemStatus,
        user_id: str = "EXAMINER_01",
        notes: str = ""
    ) -> Tuple[ReviewQueueItem, AuditLog]:
        """Update ReviewQueueItem status and record immutable AuditLog entry."""
        item = db.query(ReviewQueueItem).filter(ReviewQueueItem.id == queue_item_id).first()
        if not item:
            raise ValueError(f"ReviewQueueItem '{queue_item_id}' not found.")

        old_status = item.status.value if item.status else "NEW"
        item.status = new_status
        db.commit()
        db.refresh(item)

        # Create AuditLog entry
        audit = AuditLog(
            id=uuid.uuid4(),
            user_id=user_id,
            action="UPDATE_QUEUE_ITEM_STATUS",
            entity_type="ReviewQueueItem",
            entity_id=str(item.id),
            timestamp=datetime.now(timezone.utc),
            before_after_json={
                "previous_status": old_status,
                "new_status": new_status.value,
                "notes": notes,
                "finding_id": str(item.finding_id),
                "cse_id": str(item.cse_id)
            },
            analysis_run_id=item.analysis_run_id
        )
        db.add(audit)
        db.commit()
        db.refresh(audit)

        return item, audit
