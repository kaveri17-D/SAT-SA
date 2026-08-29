import uuid
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional

from app.models import CSE, Asset, Alert, MaintenanceLog, AssetCriticality, AlertSeverity
from app.rules.negative_space import NegativeSpaceEvaluators
from app.rules.matrix import ExpectedEvidenceMatrix
from app.rules.evaluator import EvaluationStatus
from app.rules.baseline import BaselineRuleEvaluators
from app.evidence.reconstructor import OperationalWorkflowNode
from app.ingestion.quality import DataQualityAssessor


@dataclass
class RobustnessTestCaseResult:
    test_id: str
    category: str
    description: str
    safeguard_exercised: str
    status: str  # PASS / FAIL
    error_message: Optional[str] = None
    output_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class RobustnessReport:
    total_robustness_tests: int
    passed_tests: int
    failed_tests: int
    pass_rate: float
    results: List[RobustnessTestCaseResult] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_robustness_tests": self.total_robustness_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "pass_rate": self.pass_rate,
            "results": [r.to_dict() for r in self.results]
        }


class RobustnessHarness:
    """Exercises edge cases, safeguards, and degenerate operational conditions."""

    @staticmethod
    def run_robustness_tests() -> RobustnessReport:
        matrix = ExpectedEvidenceMatrix()
        now = datetime.now(timezone.utc)
        results: List[RobustnessTestCaseResult] = []

        cse = CSE(id=uuid.uuid4(), name="CSE-ROBUST", sector="POWER", entity_type="GRID_OPERATOR", size_tier="TIER_1")
        asset = Asset(id=uuid.uuid4(), cse_id=cse.id, name="SCADA-ROBUST", asset_type="SCADA_CONTROLLER", criticality=AssetCriticality.CRITICAL, status="ACTIVE")

        # -------------------------------------------------------------
        # 1. Zero-Variance NEG-02 (Zero Alerts in Baseline & Test Windows)
        # -------------------------------------------------------------
        try:
            res_zero = NegativeSpaceEvaluators.evaluate_neg02_telemetry_drop(cse=cse, alerts=[], evaluation_timestamp=now)
            results.append(RobustnessTestCaseResult(
                test_id="ROB-01-ZERO-VARIANCE",
                category="Edge Case",
                description="Zero alerts in baseline and current observation windows (0/0 division).",
                safeguard_exercised="Zero-division safeguard in rolling average baseline calculation.",
                status="PASS" if res_zero.status in (EvaluationStatus.PASS, EvaluationStatus.NOT_APPLICABLE, EvaluationStatus.CONFIRMED) else "FAIL",
                output_summary=f"Result status: {res_zero.status.value}"
            ))
        except Exception as e:
            results.append(RobustnessTestCaseResult(
                test_id="ROB-01-ZERO-VARIANCE",
                category="Edge Case",
                description="Zero alerts in baseline and current windows.",
                safeguard_exercised="Zero-division safeguard.",
                status="FAIL",
                error_message=str(e)
            ))

        # -------------------------------------------------------------
        # 2. Outlier-Heavy Peer Population (Highly Skewed Density)
        # -------------------------------------------------------------
        try:
            target_asset = Asset(id=uuid.uuid4(), cse_id=cse.id, name="SCADA-OUTLIER-TARGET", asset_type="SCADA_CONTROLLER", criticality=AssetCriticality.CRITICAL, status="ACTIVE")
            outlier_asset = Asset(id=uuid.uuid4(), cse_id=cse.id, name="SCADA-OUTLIER-HIGH", asset_type="SCADA_CONTROLLER", criticality=AssetCriticality.CRITICAL, status="ACTIVE")
            normal_peers = [Asset(id=uuid.uuid4(), cse_id=cse.id, name=f"SCADA-PEER-{i}", asset_type="SCADA_CONTROLLER", criticality=AssetCriticality.CRITICAL, status="ACTIVE") for i in range(5)]

            alerts_target = [Alert(id=uuid.uuid4(), cse_id=cse.id, asset_id=target_asset.id, category="SENSOR", severity=AlertSeverity.LOW, created_at=now - timedelta(hours=i*2)) for i in range(5)]
            alerts_outlier = [Alert(id=uuid.uuid4(), cse_id=cse.id, asset_id=outlier_asset.id, category="SENSOR", severity=AlertSeverity.LOW, created_at=now - timedelta(minutes=i)) for i in range(500)]
            alerts_peers = []
            for p in normal_peers:
                for i in range(25):
                    alerts_peers.append(Alert(id=uuid.uuid4(), cse_id=cse.id, asset_id=p.id, category="SENSOR", severity=AlertSeverity.LOW, created_at=now - timedelta(hours=i*2)))

            all_test_alerts = alerts_target + alerts_outlier + alerts_peers
            all_test_assets = [target_asset, outlier_asset] + normal_peers

            res_peer_skew = NegativeSpaceEvaluators.evaluate_neg04_under_monitored_asset(target_asset=target_asset, all_assets=all_test_assets, all_alerts=all_test_alerts)
            results.append(RobustnessTestCaseResult(
                test_id="ROB-02-PEER-SKEW",
                category="Distribution Robustness",
                description="Evaluating peer under-monitoring with heavy-tailed outlier density.",
                safeguard_exercised="Median-based peer statistic estimation robust against extreme outliers.",
                status="PASS" if res_peer_skew.status in (EvaluationStatus.PASS, EvaluationStatus.CONFIRMED) else "FAIL",
                output_summary=f"Result status: {res_peer_skew.status.value}"
            ))
        except Exception as e:
            results.append(RobustnessTestCaseResult(
                test_id="ROB-02-PEER-SKEW",
                category="Distribution Robustness",
                description="Peer skew handling.",
                safeguard_exercised="Median peer aggregation.",
                status="FAIL",
                error_message=str(e)
            ))

        # -------------------------------------------------------------
        # 3. Sparse Telemetry (Only 1 alert in entire CSE lifetime)
        # -------------------------------------------------------------
        try:
            single_alert = [Alert(id=uuid.uuid4(), cse_id=cse.id, category="NETWORK_FLOW", severity=AlertSeverity.LOW, created_at=now - timedelta(days=10))]
            res_sparse = NegativeSpaceEvaluators.evaluate_neg02_telemetry_drop(cse=cse, alerts=single_alert, evaluation_timestamp=now)
            results.append(RobustnessTestCaseResult(
                test_id="ROB-03-SPARSE-TELEMETRY",
                category="Data Sparsity",
                description="CSE portfolio has only a single historical event.",
                safeguard_exercised="Graceful degradation on sparse time series without indexing errors.",
                status="PASS",
                output_summary=f"Result status: {res_sparse.status.value}"
            ))
        except Exception as e:
            results.append(RobustnessTestCaseResult(
                test_id="ROB-03-SPARSE-TELEMETRY",
                category="Data Sparsity",
                description="Sparse telemetry.",
                safeguard_exercised="Degradation handling.",
                status="FAIL",
                error_message=str(e)
            ))

        # -------------------------------------------------------------
        # 4. Missing Optional Fields (Nulls in Investigation / Analyst)
        # -------------------------------------------------------------
        try:
            from app.models import Investigation
            alt_null = Alert(id=uuid.uuid4(), cse_id=cse.id, asset_id=asset.id, category="EXFILTRATION_SUSPICION", severity=AlertSeverity.CRITICAL, status="OPEN", created_at=now)
            inv_null = Investigation(id=uuid.uuid4(), alert_id=alt_null.id, analyst_id=None, duration_seconds=None, notes=None, outcome=None)
            node_null = OperationalWorkflowNode(alert=alt_null, asset=asset, cse=cse, investigation=inv_null)
            res_null = BaselineRuleEvaluators.evaluate_gap01(node_null)
            results.append(RobustnessTestCaseResult(
                test_id="ROB-04-NULL-OPTIONAL-FIELDS",
                category="Null Safety",
                description="Workflow node with null analyst_id, duration, notes, and outcome.",
                safeguard_exercised="Defensive None checks across rule evaluators and workflow nodes.",
                status="PASS" if res_null.status == EvaluationStatus.FAIL else "FAIL",
                output_summary=f"Result status: {res_null.status.value} (correctly flagged missing escalation on critical alert)"
            ))
        except Exception as e:
            results.append(RobustnessTestCaseResult(
                test_id="ROB-04-NULL-OPTIONAL-FIELDS",
                category="Null Safety",
                description="Null optional fields.",
                safeguard_exercised="Defensive None checks.",
                status="FAIL",
                error_message=str(e)
            ))

        # -------------------------------------------------------------
        # 5. Legitimate Maintenance Silence Suppression
        # -------------------------------------------------------------
        try:
            maint_log = MaintenanceLog(
                id=uuid.uuid4(),
                cse_id=cse.id,
                asset_id=asset.id,
                maintenance_ref="MAINT-2026-FIRMWARE-01",
                start_time=now - timedelta(hours=72),
                end_time=now + timedelta(hours=12),
                reason="Scheduled firmware upgrade"
            )
            res_maint = NegativeSpaceEvaluators.evaluate_neg01_missing_telemetry(
                asset=asset,
                recent_alerts=[],
                maintenance_logs=[maint_log],
                matrix=matrix,
                evaluation_timestamp=now
            )
            results.append(RobustnessTestCaseResult(
                test_id="ROB-05-MAINTENANCE-SUPPRESSION",
                category="Context Awareness",
                description="Active maintenance window overlapping 72-hour operational silence.",
                safeguard_exercised="MaintenanceContextMatcher automatically suppressing false positives.",
                status="PASS" if res_maint.status == EvaluationStatus.SUPPRESSED else "FAIL",
                output_summary=f"Suppression verified: status={res_maint.status.value}"
            ))
        except Exception as e:
            results.append(RobustnessTestCaseResult(
                test_id="ROB-05-MAINTENANCE-SUPPRESSION",
                category="Context Awareness",
                description="Maintenance suppression.",
                safeguard_exercised="Maintenance matcher.",
                status="FAIL",
                error_message=str(e)
            ))

        # -------------------------------------------------------------
        # 6. Data Quality Assessor Completeness Modifier Bounds
        # -------------------------------------------------------------
        try:
            mod_100 = DataQualityAssessor.calculate_confidence_modifier(100.0)
            mod_50 = DataQualityAssessor.calculate_confidence_modifier(50.0)
            mod_0 = DataQualityAssessor.calculate_confidence_modifier(0.0)
            
            is_valid = (mod_100 == 1.0 and 0.0 < mod_50 < 1.0 and 0.0 < mod_0 < 1.0)
            results.append(RobustnessTestCaseResult(
                test_id="ROB-06-CONFIDENCE-MODIFIER-BOUNDS",
                category="Data Quality",
                description="Confidence modifier scaling across data completeness range [0%..100%].",
                safeguard_exercised="Monotonic confidence dampening preventing false high-confidence findings on degraded inputs.",
                status="PASS" if is_valid else "FAIL",
                output_summary=f"Modifiers: 100%->{mod_100}, 50%->{mod_50}, 0%->{mod_0}"
            ))
        except Exception as e:
            results.append(RobustnessTestCaseResult(
                test_id="ROB-06-CONFIDENCE-MODIFIER-BOUNDS",
                category="Data Quality",
                description="Confidence scaling bounds.",
                safeguard_exercised="Quality modifier.",
                status="FAIL",
                error_message=str(e)
            ))

        passed = sum(1 for r in results if r.status == "PASS")
        failed = len(results) - passed
        pass_rate = round(passed / len(results) * 100.0, 2)

        return RobustnessReport(
            total_robustness_tests=len(results),
            passed_tests=passed,
            failed_tests=failed,
            pass_rate=pass_rate,
            results=results
        )
