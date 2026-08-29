import json
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from app.models import Finding, AnalysisRun


@dataclass
class RuleMetricReport:
    rule_id: str
    true_positives: int = 0
    false_positives: int = 0
    false_negatives: int = 0
    true_negatives: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    false_positive_rate: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "true_negatives": self.true_negatives,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "false_positive_rate": self.false_positive_rate
        }


@dataclass
class EvaluationReport:
    total_ground_truth_scenarios: int
    true_positives: int
    false_positives: int
    false_negatives: int
    true_negatives: int
    precision: float
    recall: float
    f1_score: float
    false_positive_rate: float
    findings_generated: int
    quarantined_false_positive_exceptions: int
    per_rule_metrics: Dict[str, RuleMetricReport] = field(default_factory=dict)
    macro_precision: float = 0.0
    macro_recall: float = 0.0
    macro_f1_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_ground_truth_scenarios": self.total_ground_truth_scenarios,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "true_negatives": self.true_negatives,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "false_positive_rate": self.false_positive_rate,
            "macro_precision": self.macro_precision,
            "macro_recall": self.macro_recall,
            "macro_f1_score": self.macro_f1_score,
            "per_rule_metrics": {k: v.to_dict() for k, v in self.per_rule_metrics.items()},
            "findings_generated": self.findings_generated,
            "quarantined_false_positive_exceptions": self.quarantined_false_positive_exceptions
        }


class GroundTruthEvaluator:
    """Independent evaluation metric calculator comparing engine findings against synthetic ground truth."""

    @staticmethod
    def evaluate_analysis_run(db: Session, analysis_run_id: str, ground_truth_manifest_path: str) -> EvaluationReport:
        """Calculate per-rule and macro Precision, Recall, F1 against ground-truth manifest."""
        with open(ground_truth_manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        gt_scenarios = manifest.get("ground_truth_scenarios", [])
        
        # Determine evaluated rules for this analysis run
        import uuid
        run_obj = db.query(AnalysisRun).filter(AnalysisRun.id == uuid.UUID(str(analysis_run_id))).first() if analysis_run_id else None
        engine_name = run_obj.configuration.get("engine", "") if run_obj and run_obj.configuration else ""

        evaluated_rules = None
        if engine_name == "ExecutionGapEngine":
            evaluated_rules = {"GAP-01", "GAP-02", "GAP-03", "GAP-04", "GAP-05", "GAP-06"}
        elif engine_name == "NegativeSpaceEngine":
            evaluated_rules = {"NEG-01", "NEG-02", "NEG-03", "NEG-04", "NEG-05"}

        # Filter expected ground truth anomaly targets (excluding legitimate exceptions)
        anomaly_gt = [
            s for s in gt_scenarios 
            if s["scenario_class"] in ("EXECUTION_GAP", "NEGATIVE_SPACE", "PEER_ANOMALY", "MIXED_SIGNAL") 
            and not s.get("is_legitimate_exception", False)
            and (evaluated_rules is None or s.get("expected_finding_rule") in evaluated_rules)
        ]
        
        legitimate_exceptions_gt = [
            s for s in gt_scenarios if s.get("is_legitimate_exception", False)
        ]

        gt_by_rule: Dict[str, List[Dict[str, Any]]] = {}
        for s in anomaly_gt:
            rule_id = s.get("expected_finding_rule") or "UNKNOWN_RULE"
            gt_by_rule.setdefault(rule_id, []).append(s)

        findings = db.query(Finding).filter(Finding.analysis_run_id == analysis_run_id).all()
        findings_by_rule: Dict[str, List[Finding]] = {}
        for f in findings:
            findings_by_rule.setdefault(f.rule_id, []).append(f)

        per_rule_reports: Dict[str, RuleMetricReport] = {}
        all_rules = set(gt_by_rule.keys()).union(set(findings_by_rule.keys()))

        total_tp = 0
        total_fp = 0
        total_fn = 0

        for rule in sorted(all_rules):
            rule_gt = gt_by_rule.get(rule, [])
            rule_findings = findings_by_rule.get(rule, [])

            gt_target_ids = {str(s["target_entity_id"]) for s in rule_gt}

            rule_tp = 0
            rule_fp = 0

            for finding in rule_findings:
                matched = False
                if str(finding.cse_id) in gt_target_ids or str(finding.asset_id) in gt_target_ids:
                    matched = True
                else:
                    for ref in finding.evidence_refs:
                        if str(ref.get("source_record_id")) in gt_target_ids:
                            matched = True
                            break
                
                if matched:
                    rule_tp += 1
                else:
                    rule_fp += 1

            # Determine candidate evaluation scope for TN calculation
            if rule in ("NEG-01", "NEG-04", "NEG-05", "GAP-01", "GAP-02", "GAP-03", "GAP-04", "GAP-05", "GAP-06"):
                from app.models import Asset
                total_candidates = db.query(Asset).count()
            else:
                from app.models import CSE
                total_candidates = db.query(CSE).count()

            rule_fn = max(0, len(rule_gt) - rule_tp)
            rule_tn = max(0, total_candidates - (rule_tp + rule_fp + rule_fn))

            rule_prec = round(rule_tp / (rule_tp + rule_fp), 4) if (rule_tp + rule_fp) > 0 else (1.0 if len(rule_gt) == 0 and rule_fp == 0 else 0.0)
            rule_rec = round(rule_tp / (rule_tp + rule_fn), 4) if (rule_tp + rule_fn) > 0 else (1.0 if len(rule_gt) == 0 else 0.0)
            rule_f1 = round((2 * rule_prec * rule_rec) / (rule_prec + rule_rec), 4) if (rule_prec + rule_rec) > 0 else 0.0
            rule_fpr = round(rule_fp / (rule_fp + rule_tn), 4) if (rule_fp + rule_tn) > 0 else 0.0

            per_rule_reports[rule] = RuleMetricReport(
                rule_id=rule,
                true_positives=rule_tp,
                false_positives=rule_fp,
                false_negatives=rule_fn,
                true_negatives=rule_tn,
                precision=rule_prec,
                recall=rule_rec,
                f1_score=rule_f1,
                false_positive_rate=rule_fpr
            )

            total_tp += rule_tp
            total_fp += rule_fp
            total_fn += rule_fn

        total_tn = sum(r.true_negatives for r in per_rule_reports.values())
        overall_prec = round(total_tp / (total_tp + total_fp), 4) if (total_tp + total_fp) > 0 else 0.0
        overall_rec = round(total_tp / (total_tp + total_fn), 4) if (total_tp + total_fn) > 0 else 0.0
        overall_f1 = round((2 * overall_prec * overall_rec) / (overall_prec + overall_rec), 4) if (overall_prec + overall_rec) > 0 else 0.0
        overall_fpr = round(total_fp / (total_fp + total_tn), 4) if (total_fp + total_tn) > 0 else 0.0

        prec_list = [r.precision for r in per_rule_reports.values()]
        rec_list = [r.recall for r in per_rule_reports.values()]
        f1_list = [r.f1_score for r in per_rule_reports.values()]

        macro_prec = round(sum(prec_list) / len(prec_list), 4) if prec_list else 0.0
        macro_rec = round(sum(rec_list) / len(rec_list), 4) if rec_list else 0.0
        macro_f1 = round(sum(f1_list) / len(f1_list), 4) if f1_list else 0.0

        return EvaluationReport(
            total_ground_truth_scenarios=len(anomaly_gt),
            true_positives=total_tp,
            false_positives=total_fp,
            false_negatives=total_fn,
            true_negatives=total_tn,
            precision=overall_prec,
            recall=overall_rec,
            f1_score=overall_f1,
            false_positive_rate=overall_fpr,
            macro_precision=macro_prec,
            macro_recall=macro_rec,
            macro_f1_score=macro_f1,
            per_rule_metrics=per_rule_reports,
            findings_generated=len(findings),
            quarantined_false_positive_exceptions=len(legitimate_exceptions_gt)
        )
