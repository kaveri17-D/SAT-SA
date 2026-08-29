from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any
import uuid

from app.models import Asset, CSE, Alert, MaintenanceLog, AssetCriticality, AlertSeverity
from app.rules.negative_space import NegativeSpaceEvaluators
from app.rules.matrix import ExpectedEvidenceMatrix
from app.rules.evaluator import EvaluationStatus
from app.rules.baseline import BaselineRuleEvaluators
from app.evidence.reconstructor import OperationalWorkflowNode


@dataclass
class ThresholdSensitivityPoint:
    rule_id: str
    parameter_name: str
    configured_threshold: float
    tested_value: float
    expected_status: str
    observed_status: str
    is_consistent: bool
    explanation: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SensitivityReport:
    total_boundary_tests: int
    consistent_tests: int
    consistency_rate: float
    test_points: List[ThresholdSensitivityPoint] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_boundary_tests": self.total_boundary_tests,
            "consistent_tests": self.consistent_tests,
            "consistency_rate": self.consistency_rate,
            "test_points": [p.to_dict() for p in self.test_points]
        }


class ThresholdSensitivityHarness:
    """Evaluates mathematical boundary consistency around established production thresholds without modifying production values."""

    @staticmethod
    def run_sensitivity_analysis() -> SensitivityReport:
        matrix = ExpectedEvidenceMatrix()
        now = datetime.now(timezone.utc)
        points: List[ThresholdSensitivityPoint] = []

        # -------------------------------------------------------------
        # 1. NEG-01: Silence Threshold Boundaries (48.0 Hours)
        # -------------------------------------------------------------
        cse = CSE(id=uuid.uuid4(), name="CSE-SENS", sector="POWER", entity_type="GRID_OPERATOR", size_tier="TIER_1")
        asset = Asset(id=uuid.uuid4(), cse_id=cse.id, name="SCADA-SENS", asset_type="SCADA_CONTROLLER", criticality=AssetCriticality.CRITICAL, status="ACTIVE")

        # 1a. Sub-threshold: 47.9 hours of silence (within allowed 48h limit -> PASS)
        alert_47_9h = [Alert(id=uuid.uuid4(), cse_id=cse.id, asset_id=asset.id, category="TELEMETRY_HEARTBEAT", severity=AlertSeverity.LOW, created_at=now - timedelta(hours=47.9))]
        res_47_9 = NegativeSpaceEvaluators.evaluate_neg01_missing_telemetry(asset=asset, recent_alerts=alert_47_9h, maintenance_logs=[], matrix=matrix, evaluation_timestamp=now)
        points.append(ThresholdSensitivityPoint(
            rule_id="NEG-01",
            parameter_name="silence_threshold_hours",
            configured_threshold=48.0,
            tested_value=47.9,
            expected_status="PASS",
            observed_status=res_47_9.status.value,
            is_consistent=(res_47_9.status == EvaluationStatus.PASS),
            explanation="Recent alert at 47.9h is within 48h threshold; no silence finding generated."
        ))

        # 1b. Super-threshold: 48.1 hours of silence (exceeds allowed 48h limit -> CONFIRMED)
        alert_48_1h = [Alert(id=uuid.uuid4(), cse_id=cse.id, asset_id=asset.id, category="TELEMETRY_HEARTBEAT", severity=AlertSeverity.LOW, created_at=now - timedelta(hours=48.1))]
        res_48_1 = NegativeSpaceEvaluators.evaluate_neg01_missing_telemetry(asset=asset, recent_alerts=alert_48_1h, maintenance_logs=[], matrix=matrix, evaluation_timestamp=now)
        points.append(ThresholdSensitivityPoint(
            rule_id="NEG-01",
            parameter_name="silence_threshold_hours",
            configured_threshold=48.0,
            tested_value=48.1,
            expected_status="CONFIRMED",
            observed_status=res_48_1.status.value,
            is_consistent=(res_48_1.status == EvaluationStatus.CONFIRMED),
            explanation="Recent alert at 48.1h exceeds 48.0h threshold; silence finding correctly triggered."
        ))

        # -------------------------------------------------------------
        # 2. NEG-02: Telemetry Volume Drop (75.0% Drop Threshold)
        # -------------------------------------------------------------
        cutoff_baseline = now - timedelta(days=30)
        alerts_baseline = []
        for day_idx in range(30):
            bin_time = cutoff_baseline + timedelta(days=day_idx, hours=12)
            if bin_time < (now - timedelta(hours=24)):  # Baseline 10 alerts/day
                for _ in range(10):
                    alerts_baseline.append(Alert(
                        id=uuid.uuid4(), cse_id=cse.id, category="SENSOR", severity=AlertSeverity.LOW, created_at=bin_time
                    ))

        # 2a. 50% drop (5 alerts in last 24h vs 10/day -> PASS with 75% threshold)
        alerts_50 = list(alerts_baseline)
        for _ in range(5):
            alerts_50.append(Alert(id=uuid.uuid4(), cse_id=cse.id, category="SENSOR", severity=AlertSeverity.LOW, created_at=now - timedelta(hours=12)))
        res_neg02_50 = NegativeSpaceEvaluators.evaluate_neg02_telemetry_drop(cse=cse, alerts=alerts_50, drop_threshold_pct=75.0, evaluation_timestamp=now)
        points.append(ThresholdSensitivityPoint(
            rule_id="NEG-02",
            parameter_name="drop_percentage_threshold",
            configured_threshold=75.0,
            tested_value=50.0,
            expected_status="PASS",
            observed_status=res_neg02_50.status.value,
            is_consistent=(res_neg02_50.status == EvaluationStatus.PASS),
            explanation="Volume drop of 50.0% is below 75.0% trigger threshold; finding waived."
        ))

        # 2b. 100% drop (0 alerts in last 24h vs 10/day -> CONFIRMED)
        res_neg02_100 = NegativeSpaceEvaluators.evaluate_neg02_telemetry_drop(cse=cse, alerts=alerts_baseline, drop_threshold_pct=75.0, evaluation_timestamp=now)
        points.append(ThresholdSensitivityPoint(
            rule_id="NEG-02",
            parameter_name="drop_percentage_threshold",
            configured_threshold=75.0,
            tested_value=100.0,
            expected_status="CONFIRMED",
            observed_status=res_neg02_100.status.value,
            is_consistent=(res_neg02_100.status == EvaluationStatus.CONFIRMED),
            explanation="Volume drop of 100.0% exceeds 75.0% trigger threshold; finding triggered."
        ))

        # -------------------------------------------------------------
        # 3. NEG-04: Peer Asset Density Ratio (20.0% Density Threshold)
        # -------------------------------------------------------------
        target_asset_25 = Asset(id=uuid.uuid4(), cse_id=cse.id, name="SCADA-25", asset_type="SCADA_CONTROLLER", criticality=AssetCriticality.CRITICAL, status="ACTIVE")
        peer_asset_100 = Asset(id=uuid.uuid4(), cse_id=cse.id, name="SCADA-PEER", asset_type="SCADA_CONTROLLER", criticality=AssetCriticality.CRITICAL, status="ACTIVE")
        
        alerts_peer_25 = [Alert(id=uuid.uuid4(), cse_id=cse.id, asset_id=target_asset_25.id, category="SENSOR_LOG", severity=AlertSeverity.LOW, created_at=now - timedelta(hours=i*5)) for i in range(25)]
        alerts_peer_100 = [Alert(id=uuid.uuid4(), cse_id=cse.id, asset_id=peer_asset_100.id, category="SENSOR_LOG", severity=AlertSeverity.LOW, created_at=now - timedelta(hours=i*2)) for i in range(100)]
        all_alerts_25 = alerts_peer_25 + alerts_peer_100
        
        res_neg04_25 = NegativeSpaceEvaluators.evaluate_neg04_under_monitored_asset(target_asset=target_asset_25, all_assets=[target_asset_25, peer_asset_100], all_alerts=all_alerts_25)
        points.append(ThresholdSensitivityPoint(
            rule_id="NEG-04",
            parameter_name="peer_density_ratio_threshold",
            configured_threshold=0.20,
            tested_value=0.25,
            expected_status="PASS",
            observed_status=res_neg04_25.status.value,
            is_consistent=(res_neg04_25.status == EvaluationStatus.PASS),
            explanation="Asset alert density is 25% of peer median (>= 20%); no under-monitoring finding."
        ))

        # Target asset = 10 alerts (10% < 20% -> CONFIRMED)
        target_asset_10 = Asset(id=uuid.uuid4(), cse_id=cse.id, name="SCADA-10", asset_type="SCADA_CONTROLLER", criticality=AssetCriticality.CRITICAL, status="ACTIVE")
        alerts_peer_10 = [Alert(id=uuid.uuid4(), cse_id=cse.id, asset_id=target_asset_10.id, category="SENSOR_LOG", severity=AlertSeverity.LOW, created_at=now - timedelta(hours=i*10)) for i in range(10)]
        all_alerts_10 = alerts_peer_10 + alerts_peer_100
        res_neg04_10 = NegativeSpaceEvaluators.evaluate_neg04_under_monitored_asset(target_asset=target_asset_10, all_assets=[target_asset_10, peer_asset_100], all_alerts=all_alerts_10)
        points.append(ThresholdSensitivityPoint(
            rule_id="NEG-04",
            parameter_name="peer_density_ratio_threshold",
            configured_threshold=0.20,
            tested_value=0.10,
            expected_status="CONFIRMED",
            observed_status=res_neg04_10.status.value,
            is_consistent=(res_neg04_10.status == EvaluationStatus.CONFIRMED),
            explanation="Asset alert density is 10% of peer median (< 20%); under-monitoring finding triggered."
        ))

        # -------------------------------------------------------------
        # 4. GAP-03: Hasty Duration Threshold (15.0s Threshold)
        # -------------------------------------------------------------
        from app.models import Investigation
        alt_test = Alert(id=uuid.uuid4(), cse_id=cse.id, asset_id=asset.id, category="MALWARE_DETECTION", severity=AlertSeverity.HIGH, status="CLOSED", created_at=now)
        
        # 4a. 16s duration (> 15s -> PASS)
        inv_16s = Investigation(id=uuid.uuid4(), alert_id=alt_test.id, duration_seconds=16, outcome="RESOLVED")
        node_16s = OperationalWorkflowNode(alert=alt_test, asset=asset, cse=cse, investigation=inv_16s)
        res_gap03_16 = BaselineRuleEvaluators.evaluate_gap03(node_16s)
        points.append(ThresholdSensitivityPoint(
            rule_id="GAP-03",
            parameter_name="hasty_duration_seconds",
            configured_threshold=15.0,
            tested_value=16.0,
            expected_status="PASS",
            observed_status=res_gap03_16.status.value,
            is_consistent=(res_gap03_16.status == EvaluationStatus.PASS),
            explanation="Duration of 16s is above 15s hasty closure threshold; pass."
        ))

        # 4b. 8s duration (< 15s -> FAIL)
        inv_8s = Investigation(id=uuid.uuid4(), alert_id=alt_test.id, duration_seconds=8, outcome="RESOLVED")
        node_8s = OperationalWorkflowNode(alert=alt_test, asset=asset, cse=cse, investigation=inv_8s)
        res_gap03_8 = BaselineRuleEvaluators.evaluate_gap03(node_8s)
        points.append(ThresholdSensitivityPoint(
            rule_id="GAP-03",
            parameter_name="hasty_duration_seconds",
            configured_threshold=15.0,
            tested_value=8.0,
            expected_status="FAIL",
            observed_status=res_gap03_8.status.value,
            is_consistent=(res_gap03_8.status == EvaluationStatus.FAIL),
            explanation="Duration of 8s is below 15s hasty closure threshold; finding triggered."
        ))

        consistent_count = sum(1 for p in points if p.is_consistent)
        rate = round(consistent_count / len(points) * 100.0, 2)

        return SensitivityReport(
            total_boundary_tests=len(points),
            consistent_tests=consistent_count,
            consistency_rate=rate,
            test_points=points
        )
