from typing import List, Optional
from app.models import AlertSeverity, AssetCriticality, FindingSeverity, DispositionType
from app.evidence.reconstructor import OperationalWorkflowNode
from app.rules.evaluator import RuleEvaluationResult, EvaluationStatus
from app.ingestion.quality import DataQualityAssessor


class BaselineRuleEvaluators:
    """Implementations of baseline Execution Gap rules (GAP-01 through GAP-06)."""

    @staticmethod
    def evaluate_gap01(node: OperationalWorkflowNode, completeness_score: float = 100.0) -> RuleEvaluationResult:
        """GAP-01: Critical Alert Closed Without Escalation."""
        # 1. Check Applicability: Critical severity alert on Critical asset or explicitly un-escalated CLOSED outcome
        is_critical_alert = (node.alert.severity == AlertSeverity.CRITICAL)
        is_critical_asset = (node.asset is not None and node.asset.criticality == AssetCriticality.CRITICAL)
        is_closed_outcome = (node.has_investigation and node.investigation.outcome == "CLOSED")

        is_applicable = is_critical_alert and (is_critical_asset or is_closed_outcome)

        if not is_applicable:
            return RuleEvaluationResult(
                rule_id="GAP-01",
                rule_version="1.0.0",
                target_node=node,
                status=EvaluationStatus.NOT_APPLICABLE,
                applicability=False,
                expected_behaviour="Critical alerts require escalation.",
                observed_behaviour=f"Alert severity is {node.alert.severity.value}.",
                severity=FindingSeverity.CRITICAL,
                confidence=1.0,
                risk_contribution=0.0,
                evidence_refs=[],
                explanation="Rule not applicable to non-critical alerts or routine resolved events on non-critical assets.",
                recommendation=""
            )

        # 2. Check Data Completeness / Unknown state
        if completeness_score < 50.0:
            return RuleEvaluationResult(
                rule_id="GAP-01",
                rule_version="1.0.0",
                target_node=node,
                status=EvaluationStatus.UNKNOWN,
                applicability=True,
                expected_behaviour="Escalation record required for critical alert.",
                observed_behaviour="Data export completeness is below 50%; escalation presence unknown.",
                severity=FindingSeverity.CRITICAL,
                confidence=0.40,
                risk_contribution=0.0,
                evidence_refs=node.to_evidence_refs(),
                explanation="Data export incomplete; cannot confirm if escalation record was missed or truncated.",
                recommendation="Re-run export with complete database logs."
            )

        # 3. False Positive Exception Checks (Maintenance / Decommissioned)
        if node.asset and (node.asset.status == "DECOMMISSIONED" or node.asset.decommissioned_at is not None):
            return RuleEvaluationResult(
                rule_id="GAP-01",
                rule_version="1.0.0",
                target_node=node,
                status=EvaluationStatus.PASS,
                applicability=True,
                expected_behaviour="Escalation record required for active critical alert.",
                observed_behaviour=f"Asset {node.asset.name} is DECOMMISSIONED; alert escalation waived.",
                severity=FindingSeverity.LOW,
                confidence=0.90,
                risk_contribution=0.0,
                evidence_refs=node.to_evidence_refs(),
                explanation="Alert occurred on decommissioned asset; operational exception applied.",
                recommendation=""
            )

        # 4. Trigger Condition Check: Mandatory escalation category OR explicit un-escalated CLOSED outcome
        is_mandatory_escalation_category = (node.alert.category in ("EXFILTRATION_SUSPICION", "RANSOMWARE", "DATA_EXFIL"))
        is_explicit_closed_inv = (node.has_investigation and node.investigation.outcome == "CLOSED")
        missing_escalation = not node.has_escalation

        if (is_mandatory_escalation_category or is_explicit_closed_inv) and missing_escalation:
            conf_mod = DataQualityAssessor.calculate_confidence_modifier(completeness_score)
            dur_str = f"after {node.investigation.duration_seconds}s " if (node.has_investigation and node.investigation.duration_seconds is not None) else ""
            return RuleEvaluationResult(
                rule_id="GAP-01",
                rule_version="1.0.0",
                target_node=node,
                status=EvaluationStatus.FAIL,
                applicability=True,
                expected_behaviour="Critical alerts must be escalated to Tier-2 SOC Lead for supervisory verification prior to closure.",
                observed_behaviour=f"Alert {node.alert.category} (CRITICAL) was processed {dur_str}without an Escalation record.",
                severity=FindingSeverity.CRITICAL,
                confidence=round(0.95 * conf_mod, 2),
                risk_contribution=30.0,
                evidence_refs=node.to_evidence_refs(),
                explanation="Critical alert closed without mandatory supervisory escalation.",
                recommendation="Reopen alert for supervisory Tier-2 review and audit analyst closure justification."
            )

        return RuleEvaluationResult(
            rule_id="GAP-01",
            rule_version="1.0.0",
            target_node=node,
            status=EvaluationStatus.PASS,
            applicability=True,
            expected_behaviour="Escalation record present.",
            observed_behaviour="Escalation occurred as expected.",
            severity=FindingSeverity.CRITICAL,
            confidence=1.0,
            risk_contribution=0.0,
            evidence_refs=[],
            explanation="Alert followed expected escalation workflow.",
            recommendation=""
        )

    @staticmethod
    def evaluate_gap03(node: OperationalWorkflowNode, peer_median_duration: float = 450.0, completeness_score: float = 100.0) -> RuleEvaluationResult:
        """GAP-03: Hasty Investigation Duration Significantly Below Historical Baseline."""
        if not node.has_investigation or node.investigation.duration_seconds is None:
            return RuleEvaluationResult(
                rule_id="GAP-03",
                rule_version="1.0.0",
                target_node=node,
                status=EvaluationStatus.NOT_APPLICABLE,
                applicability=False,
                expected_behaviour="Investigation duration evaluation.",
                observed_behaviour="No investigation record available.",
                severity=FindingSeverity.MEDIUM,
                confidence=1.0,
                risk_contribution=0.0,
                evidence_refs=[],
                explanation="Investigation duration not present.",
                recommendation=""
            )

        dur = node.investigation.duration_seconds
        # Hasty duration threshold: < 15 seconds (vs 450s peer median)
        if dur < 15:
            conf_mod = DataQualityAssessor.calculate_confidence_modifier(completeness_score)
            return RuleEvaluationResult(
                rule_id="GAP-03",
                rule_version="1.0.0",
                target_node=node,
                status=EvaluationStatus.FAIL,
                applicability=True,
                expected_behaviour=f"Investigation duration should align with standard operational baselines (peer median ~{peer_median_duration}s).",
                observed_behaviour=f"Investigation completed in {dur} seconds, indicating hasty superficial closure.",
                severity=FindingSeverity.MEDIUM,
                confidence=round(0.90 * conf_mod, 2),
                risk_contribution=15.0,
                evidence_refs=node.to_evidence_refs(),
                explanation="Investigation duration was 8-15 seconds, far below expected operational baseline.",
                recommendation="Audit analyst notes for templated auto-close behavior."
            )

        return RuleEvaluationResult(
            rule_id="GAP-03",
            rule_version="1.0.0",
            target_node=node,
            status=EvaluationStatus.PASS,
            applicability=True,
            expected_behaviour="Normal investigation duration.",
            observed_behaviour=f"Duration was {dur}s.",
            severity=FindingSeverity.MEDIUM,
            confidence=1.0,
            risk_contribution=0.0,
            evidence_refs=[],
            explanation="Investigation duration within baseline.",
            recommendation=""
        )
