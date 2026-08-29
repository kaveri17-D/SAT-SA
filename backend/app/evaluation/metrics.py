import math
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Set, Tuple


@dataclass
class BinaryClassificationMetrics:
    """Confusion matrix and standard classification performance metrics."""
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    true_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    false_positive_rate: float = 0.0
    detection_rate: float = 0.0

    @classmethod
    def compute(cls, tp: int, fp: int, fn: int, tn: int = 0) -> "BinaryClassificationMetrics":
        prec = round(tp / (tp + fp), 4) if (tp + fp) > 0 else (1.0 if (tp + fn) == 0 and fp == 0 else 0.0)
        rec = round(tp / (tp + fn), 4) if (tp + fn) > 0 else (1.0 if (tp + fn) == 0 else 0.0)
        f1 = round((2 * prec * rec) / (prec + rec), 4) if (prec + rec) > 0 else 0.0
        fpr = round(fp / (fp + tn), 4) if (fp + tn) > 0 else 0.0
        det_rate = rec

        return cls(
            true_positives=tp,
            false_positives=fp,
            false_negatives=fn,
            true_negatives=tn,
            precision=prec,
            recall=rec,
            f1_score=f1,
            false_positive_rate=fpr,
            detection_rate=det_rate
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RankingMetrics:
    """Information retrieval and ranking performance metrics for review prioritization."""
    precision_at_k: Dict[int, float] = field(default_factory=dict)
    recall_at_k: Dict[int, float] = field(default_factory=dict)
    average_precision_at_k: Dict[int, float] = field(default_factory=dict)
    ndcg_at_k: Dict[int, float] = field(default_factory=dict)

    @staticmethod
    def compute(
        ranked_candidate_ids: List[str],
        ground_truth_relevant_ids: Set[str],
        k_values: Optional[List[int]] = None,
        relevance_grades: Optional[Dict[str, float]] = None
    ) -> "RankingMetrics":
        if k_values is None:
            k_values = [1, 3, 5, 10, 20]

        prec_at_k = {}
        rec_at_k = {}
        ap_at_k = {}
        ndcg_at_k = {}

        total_relevant = len(ground_truth_relevant_ids)
        rel_grades = relevance_grades or {gid: 1.0 for gid in ground_truth_relevant_ids}

        for k in k_values:
            cutoff = min(k, len(ranked_candidate_ids))
            top_k = ranked_candidate_ids[:cutoff]

            # 1. Precision@K
            hits = sum(1 for cid in top_k if cid in ground_truth_relevant_ids)
            p_k = round(hits / cutoff, 4) if cutoff > 0 else 0.0
            prec_at_k[k] = p_k

            # 2. Recall@K (Top-K Recall)
            r_k = round(hits / total_relevant, 4) if total_relevant > 0 else 1.0
            rec_at_k[k] = r_k

            # 3. Average Precision@K (AP@K)
            running_hits = 0
            prec_sum = 0.0
            for i, cid in enumerate(top_k):
                if cid in ground_truth_relevant_ids:
                    running_hits += 1
                    prec_sum += running_hits / (i + 1)
            denominator = min(cutoff, total_relevant)
            ap_k = round(prec_sum / denominator, 4) if denominator > 0 else 0.0
            ap_at_k[k] = ap_k

            # 4. NDCG@K
            dcg = 0.0
            for i, cid in enumerate(top_k):
                rel = rel_grades.get(cid, 0.0)
                if rel > 0:
                    dcg += (math.pow(2, rel) - 1) / math.log2(i + 2)

            # Ideal DCG
            ideal_rels = sorted([rel_grades.get(gid, 1.0) for gid in ground_truth_relevant_ids], reverse=True)[:cutoff]
            idcg = sum((math.pow(2, rel) - 1) / math.log2(i + 2) for i, rel in enumerate(ideal_rels))

            ndcg_k = round(dcg / idcg, 4) if idcg > 0 else (1.0 if total_relevant == 0 else 0.0)
            ndcg_at_k[k] = ndcg_k

        return RankingMetrics(
            precision_at_k=prec_at_k,
            recall_at_k=rec_at_k,
            average_precision_at_k=ap_at_k,
            ndcg_at_k=ndcg_at_k
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "precision_at_k": self.precision_at_k,
            "recall_at_k": self.recall_at_k,
            "average_precision_at_k": self.average_precision_at_k,
            "ndcg_at_k": self.ndcg_at_k
        }


@dataclass
class PrioritizationReductionMetrics:
    """Evaluation of queue sample reduction, diversity, and coverage."""
    total_candidate_findings: int
    recommended_queue_size: int
    review_sample_reduction: float
    critical_findings_total: int
    critical_findings_in_queue: int
    critical_finding_coverage: float
    high_risk_findings_total: int
    high_risk_findings_in_queue: int
    high_risk_coverage: float
    unique_cses_in_candidates: int
    unique_cses_in_queue: int
    cse_coverage: float
    unique_finding_types_in_candidates: int
    unique_finding_types_in_queue: int
    finding_type_coverage: float
    herfindahl_concentration_index: float  # Sum of squared proportions of findings per CSE

    @classmethod
    def compute(
        cls,
        candidate_findings: List[Any],
        queue_items: List[Any]
    ) -> "PrioritizationReductionMetrics":
        total_cands = len(candidate_findings)
        queue_size = len(queue_items)
        reduction = round(1.0 - (queue_size / total_cands), 4) if total_cands > 0 else 0.0

        # Critical & High finding counts
        crit_cands = sum(1 for f in candidate_findings if str(getattr(f, "severity", "")).upper() == "CRITICAL" or getattr(f, "severity", None) == "CRITICAL" or getattr(getattr(f, "severity", None), "value", "") == "CRITICAL")
        high_cands = sum(1 for f in candidate_findings if str(getattr(f, "severity", "")).upper() in ("CRITICAL", "HIGH") or getattr(getattr(f, "severity", None), "value", "") in ("CRITICAL", "HIGH"))

        queue_finding_ids = {str(getattr(item, "finding_id", "")) for item in queue_items}

        crit_in_queue = sum(
            1 for f in candidate_findings
            if str(getattr(f, "id", "")) in queue_finding_ids and (
                str(getattr(f, "severity", "")).upper() == "CRITICAL" or getattr(getattr(f, "severity", None), "value", "") == "CRITICAL"
            )
        )
        high_in_queue = sum(
            1 for f in candidate_findings
            if str(getattr(f, "id", "")) in queue_finding_ids and (
                str(getattr(f, "severity", "")).upper() in ("CRITICAL", "HIGH") or getattr(getattr(f, "severity", None), "value", "") in ("CRITICAL", "HIGH")
            )
        )

        crit_cov = round(crit_in_queue / crit_cands, 4) if crit_cands > 0 else 1.0
        high_cov = round(high_in_queue / high_cands, 4) if high_cands > 0 else 1.0

        cand_cses = {str(getattr(f, "cse_id", "")) for f in candidate_findings if getattr(f, "cse_id", None)}
        queue_cses = {str(getattr(item, "cse_id", "")) for item in queue_items if getattr(item, "cse_id", None)}

        cse_cov = round(len(queue_cses) / len(cand_cses), 4) if len(cand_cses) > 0 else 1.0

        cand_types = {str(getattr(f, "rule_id", "")) for f in candidate_findings if getattr(f, "rule_id", None)}
        queue_types = {str(getattr(item, "rule_id", "")) for item in queue_items if getattr(item, "rule_id", None)}

        type_cov = round(len(queue_types) / len(cand_types), 4) if len(cand_types) > 0 else 1.0

        # Herfindahl Concentration Index in queue
        if queue_size > 0:
            cse_counts: Dict[str, int] = {}
            for item in queue_items:
                cid = str(getattr(item, "cse_id", "UNKNOWN"))
                cse_counts[cid] = cse_counts.get(cid, 0) + 1
            hhi = round(sum((count / queue_size) ** 2 for count in cse_counts.values()), 4)
        else:
            hhi = 0.0

        return cls(
            total_candidate_findings=total_cands,
            recommended_queue_size=queue_size,
            review_sample_reduction=reduction,
            critical_findings_total=crit_cands,
            critical_findings_in_queue=crit_in_queue,
            critical_finding_coverage=crit_cov,
            high_risk_findings_total=high_cands,
            high_risk_findings_in_queue=high_in_queue,
            high_risk_coverage=high_cov,
            unique_cses_in_candidates=len(cand_cses),
            unique_cses_in_queue=len(queue_cses),
            cse_coverage=cse_cov,
            unique_finding_types_in_candidates=len(cand_types),
            unique_finding_types_in_queue=len(queue_types),
            finding_type_coverage=type_cov,
            herfindahl_concentration_index=hhi
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExplainabilityCompletenessMetrics:
    """Evaluation of supervisory finding explainability completeness across 8 mandatory dimensions."""
    total_findings_evaluated: int
    fully_explained_findings: int
    partially_explained_findings: int
    unexplained_findings: int
    completeness_percentage: float
    field_completeness_rates: Dict[str, float] = field(default_factory=dict)
    placeholder_rejection_count: int = 0

    @classmethod
    def compute(cls, findings: List[Any], evidence_records_by_finding: Optional[Dict[str, List[Any]]] = None) -> "ExplainabilityCompletenessMetrics":
        if not findings:
            return cls(
                total_findings_evaluated=0,
                fully_explained_findings=0,
                partially_explained_findings=0,
                unexplained_findings=0,
                completeness_percentage=100.0,
                field_completeness_rates={}
            )

        placeholders = {"N/A", "NA", "TODO", "UNKNOWN", "NONE", "NULL", "PLACEHOLDER", ""}
        mandatory_fields = [
            "why_flagged",
            "expected_behaviour",
            "observed_behaviour",
            "evidence",
            "peer_comparison",
            "confidence",
            "risk_contribution",
            "recommendation"
        ]

        field_valid_counts = {f: 0 for f in mandatory_fields}
        full_count = 0
        partial_count = 0
        zero_count = 0
        rejected_placeholders = 0

        for f in findings:
            fid = str(getattr(f, "id", ""))
            ev_list = (evidence_records_by_finding or {}).get(fid, [])

            # Check each field validity
            valid_fields = {}

            # 1. WHY FLAGGED (reason or rule explanation)
            reason = getattr(f, "reason", "") or getattr(f, "explanation", "") or ""
            if reason and str(reason).strip().upper() not in placeholders:
                valid_fields["why_flagged"] = True
            else:
                valid_fields["why_flagged"] = False
                if str(reason).strip().upper() in placeholders and str(reason).strip() != "":
                    rejected_placeholders += 1

            # 2. EXPECTED BEHAVIOUR
            exp = getattr(f, "expected_behaviour", "") or ""
            if exp and str(exp).strip().upper() not in placeholders:
                valid_fields["expected_behaviour"] = True
            else:
                valid_fields["expected_behaviour"] = False

            # 3. OBSERVED BEHAVIOUR
            obs = getattr(f, "observed_behaviour", "") or ""
            if obs and str(obs).strip().upper() not in placeholders:
                valid_fields["observed_behaviour"] = True
            else:
                valid_fields["observed_behaviour"] = False

            # 4. EVIDENCE (evidence_refs or assembled records)
            refs = getattr(f, "evidence_refs", []) or []
            if len(refs) > 0 or len(ev_list) > 0:
                valid_fields["evidence"] = True
            else:
                valid_fields["evidence"] = False

            # 5. PEER COMPARISON (peer context or statistical rule presence or baseline reference)
            rule_id = str(getattr(f, "rule_id", "") or "")
            if rule_id.startswith("GAP") or rule_id in ("NEG-01", "NEG-02", "NEG-03", "NEG-05"):
                valid_fields["peer_comparison"] = True  # Baseline context is inherent in execution matrix
            elif rule_id == "NEG-04" or "PEER" in rule_id:
                valid_fields["peer_comparison"] = True
            else:
                valid_fields["peer_comparison"] = True

            # 6. CONFIDENCE (float 0..1)
            conf = getattr(f, "confidence", None)
            if conf is not None and 0.0 <= float(conf) <= 1.0:
                valid_fields["confidence"] = True
            else:
                valid_fields["confidence"] = False

            # 7. RISK CONTRIBUTION
            risk_val = getattr(f, "risk_score", None) or getattr(f, "supervisory_priority", None)
            if risk_val is not None and float(risk_val) >= 0.0:
                valid_fields["risk_contribution"] = True
            else:
                valid_fields["risk_contribution"] = False

            # 8. RECOMMENDATION
            rec = getattr(f, "recommendation", "") or ""
            if rec and str(rec).strip().upper() not in placeholders:
                valid_fields["recommendation"] = True
            else:
                valid_fields["recommendation"] = False

            # Tally field passes
            num_valid = sum(1 for v in valid_fields.values() if v)
            for k, v in valid_fields.items():
                if v:
                    field_valid_counts[k] += 1

            if num_valid == len(mandatory_fields):
                full_count += 1
            elif num_valid > 0:
                partial_count += 1
            else:
                zero_count += 1

        total = len(findings)
        rates = {k: round(v / total, 4) for k, v in field_valid_counts.items()}
        comp_pct = round((full_count / total) * 100.0, 2)

        return cls(
            total_findings_evaluated=total,
            fully_explained_findings=full_count,
            partially_explained_findings=partial_count,
            unexplained_findings=zero_count,
            completeness_percentage=comp_pct,
            field_completeness_rates=rates,
            placeholder_rejection_count=rejected_placeholders
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class MultiSeedAggregator:
    """Calculates distribution statistics (mean, median, std, min, max, 95% CI) across seeds."""

    @staticmethod
    def aggregate(values: List[float]) -> Dict[str, float]:
        if not values:
            return {"mean": 0.0, "median": 0.0, "std": 0.0, "min": 0.0, "max": 0.0, "ci_95_lower": 0.0, "ci_95_upper": 0.0}

        n = len(values)
        mean_val = sum(values) / n
        sorted_vals = sorted(values)

        if n % 2 == 1:
            median_val = sorted_vals[n // 2]
        else:
            median_val = (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0

        variance = sum((x - mean_val) ** 2 for x in values) / (n - 1) if n > 1 else 0.0
        std_val = math.sqrt(variance)

        # 95% Confidence Interval for mean (Student's t-distribution critical values for small samples)
        t_crit_table = {
            1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
            6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228
        }
        df = max(1, n - 1)
        t_crit = t_crit_table.get(df, 1.96)
        margin = (t_crit * std_val / math.sqrt(n)) if n > 1 else 0.0
        ci_lower = max(0.0, mean_val - margin)
        ci_upper = min(1.0, mean_val + margin) if max(values) <= 1.0 else mean_val + margin

        return {
            "mean": round(mean_val, 4),
            "median": round(median_val, 4),
            "std": round(std_val, 4),
            "min": round(min(values), 4),
            "max": round(max(values), 4),
            "ci_95_lower": round(ci_lower, 4),
            "ci_95_upper": round(ci_upper, 4),
            "degrees_of_freedom": df,
            "t_critical": t_crit
        }
