import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Set
from sqlalchemy.orm import Session
from app.models import Finding, Asset, CSE, Alert, MaintenanceLog, FindingStatus
from app.evaluation.metrics import BinaryClassificationMetrics


@dataclass
class ScenarioEvaluationResult:
    scenario_id: str
    scenario_class: str
    scenario_type: str
    expected_rule: str
    target_entity_id: str
    target_entity_type: str
    is_legitimate_exception: bool
    injected_count: int
    detected_count: int
    missed_count: int
    false_positives: int
    precision: float
    recall: float
    f1_score: float
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScenarioSuiteReport:
    total_scenarios: int
    total_injected: int
    total_detected: int
    total_missed: int
    total_false_positives: int
    precision: float
    recall: float
    f1_score: float
    per_scenario_results: List[ScenarioEvaluationResult] = field(default_factory=list)
    per_rule_metrics: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    negative_space_safety: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_scenarios": self.total_scenarios,
            "total_injected": self.total_injected,
            "total_detected": self.total_detected,
            "total_missed": self.total_missed,
            "total_false_positives": self.total_false_positives,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "per_scenario_results": [r.to_dict() for r in self.per_scenario_results],
            "per_rule_metrics": self.per_rule_metrics,
            "negative_space_safety": self.negative_space_safety
        }


class ScenarioEvaluator:
    """Evaluates scenario detection performance and context-aware false positive suppression with strict entity matching."""

    @staticmethod
    def evaluate(
        db: Session,
        analysis_run_id: str,
        ground_truth_manifest_data: Dict[str, Any]
    ) -> ScenarioSuiteReport:
        gt_scenarios = ground_truth_manifest_data.get("ground_truth_scenarios", [])
        findings = db.query(Finding).filter(Finding.analysis_run_id == analysis_run_id).all()

        # Active non-suppressed findings
        active_findings = [
            f for f in findings 
            if f.status not in (FindingStatus.SUPPRESSED, FindingStatus.DISMISSED)
            and "SUPPRESSED" not in str(f.reason).upper()
            and "SUPPRESSED" not in str(f.observed_behaviour).upper()
        ]

        findings_by_rule: Dict[str, List[Finding]] = {}
        for f in active_findings:
            findings_by_rule.setdefault(f.rule_id, []).append(f)

        scenario_results: List[ScenarioEvaluationResult] = []
        rule_tp_map: Dict[str, int] = {}
        rule_fp_map: Dict[str, int] = {}
        rule_fn_map: Dict[str, int] = {}

        # 1. Evaluate Anomaly Ground Truth Scenarios
        anomaly_scenarios = [s for s in gt_scenarios if not s.get("is_legitimate_exception", False)]
        
        for sc in anomaly_scenarios:
            sc_id = sc.get("scenario_id", "")
            sc_class = sc.get("scenario_class", "")
            sc_type = sc.get("scenario_type", "")
            exp_rule = sc.get("expected_finding_rule", "")
            target_id = str(sc.get("target_entity_id", ""))
            target_type = sc.get("target_entity_type", "")
            desc = sc.get("description", "")

            candidate_findings = findings_by_rule.get(exp_rule, [])
            matched = False

            for f in candidate_findings:
                # Strict matching based on target entity type
                if target_type == "Asset" and (str(f.asset_id) == target_id):
                    matched = True
                    break
                elif target_type == "CSE" and (str(f.cse_id) == target_id):
                    matched = True
                    break
                elif target_type in ("Alert", "Investigation", "MaintenanceLog"):
                    for ref in (f.evidence_refs or []):
                        if str(ref.get("source_record_id")) == target_id:
                            matched = True
                            break
                    if matched:
                        break
                else:
                    if str(f.cse_id) == target_id or str(f.asset_id) == target_id:
                        matched = True
                        break

            injected = 1
            detected = 1 if matched else 0
            missed = 0 if matched else 1

            p = 1.0 if detected > 0 else 0.0
            r = 1.0 if detected > 0 else 0.0
            f1 = 1.0 if detected > 0 else 0.0

            rule_tp_map[exp_rule] = rule_tp_map.get(exp_rule, 0) + detected
            rule_fn_map[exp_rule] = rule_fn_map.get(exp_rule, 0) + missed

            scenario_results.append(ScenarioEvaluationResult(
                scenario_id=sc_id,
                scenario_class=sc_class,
                scenario_type=sc_type,
                expected_rule=exp_rule,
                target_entity_id=target_id,
                target_entity_type=target_type,
                is_legitimate_exception=False,
                injected_count=injected,
                detected_count=detected,
                missed_count=missed,
                false_positives=0,
                precision=p,
                recall=r,
                f1_score=f1,
                description=desc
            ))

        # 2. Calculate per-rule false positives
        all_rules = set(findings_by_rule.keys()).union(set(rule_tp_map.keys()))
        for rule in all_rules:
            rule_findings = findings_by_rule.get(rule, [])
            rule_gt_targets = {
                str(s["target_entity_id"]) for s in anomaly_scenarios if s.get("expected_finding_rule") == rule
            }
            fp_count = 0
            for f in rule_findings:
                matched_gt = False
                if str(f.cse_id) in rule_gt_targets or str(f.asset_id) in rule_gt_targets:
                    matched_gt = True
                else:
                    for ref in (f.evidence_refs or []):
                        if str(ref.get("source_record_id")) in rule_gt_targets:
                            matched_gt = True
                            break
                if not matched_gt:
                    fp_count += 1
            rule_fp_map[rule] = fp_count

        # 3. Compute per-rule binary classification metrics
        per_rule_metrics: Dict[str, Dict[str, Any]] = {}
        all_assets = db.query(Asset).all()
        for rule in sorted(all_rules):
            tp = rule_tp_map.get(rule, 0)
            fp = rule_fp_map.get(rule, 0)
            fn = rule_fn_map.get(rule, 0)

            # Explicit negative population: Monitored assets/entities not flagged as positive anomalies
            tn = max(0, len(all_assets) - (tp + fp + fn))
            bcm = BinaryClassificationMetrics.compute(tp=tp, fp=fp, fn=fn, tn=tn)
            per_rule_metrics[rule] = bcm.to_dict()

        # 4. Negative Space False-Positive Safety: Legitimate Exceptions Evaluation
        legitimate_exceptions = [s for s in gt_scenarios if s.get("is_legitimate_exception", False)]
        total_legit = len(legitimate_exceptions)
        
        naive_fp_count = total_legit
        satsa_suppressed_count = 0
        satsa_false_alarms = 0

        for sc in legitimate_exceptions:
            target_id = str(sc.get("target_entity_id", ""))
            # Check if SAT-SA generated any active, unsuppressed finding on this legitimate entity
            flagged = False
            for f in active_findings:
                if str(f.cse_id) == target_id or str(f.asset_id) == target_id:
                    flagged = True
                    break
            
            if not flagged:
                satsa_suppressed_count += 1
            else:
                satsa_false_alarms += 1

        suppression_rate = round(satsa_suppressed_count / total_legit, 4) if total_legit > 0 else 1.0

        safety_report = {
            "legitimate_exception_scenarios_count": total_legit,
            "naive_absence_detector_false_positives": naive_fp_count,
            "satsa_suppressed_exceptions": satsa_suppressed_count,
            "satsa_false_alarms_on_exceptions": satsa_false_alarms,
            "exception_suppression_rate": suppression_rate,
            "false_alarm_reduction": round((naive_fp_count - satsa_false_alarms) / naive_fp_count * 100.0, 2) if naive_fp_count > 0 else 100.0
        }

        # Overall numbers
        total_injected = sum(r.injected_count for r in scenario_results)
        total_detected = sum(r.detected_count for r in scenario_results)
        total_missed = sum(r.missed_count for r in scenario_results)
        total_fp = sum(rule_fp_map.values())

        prec = round(total_detected / (total_detected + total_fp), 4) if (total_detected + total_fp) > 0 else 0.0
        rec = round(total_detected / (total_detected + total_missed), 4) if (total_detected + total_missed) > 0 else 0.0
        f1 = round((2 * prec * rec) / (prec + rec), 4) if (prec + rec) > 0 else 0.0

        return ScenarioSuiteReport(
            total_scenarios=len(scenario_results),
            total_injected=total_injected,
            total_detected=total_detected,
            total_missed=total_missed,
            total_false_positives=total_fp,
            precision=prec,
            recall=rec,
            f1_score=f1,
            per_scenario_results=scenario_results,
            per_rule_metrics=per_rule_metrics,
            negative_space_safety=safety_report
        )
