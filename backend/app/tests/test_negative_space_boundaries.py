import uuid
from datetime import datetime, timezone, timedelta
import pytest

from app.models.domain import CSE, Asset, Alert, MaintenanceLog, AssetCriticality, AlertSeverity
from app.rules.evaluator import EvaluationStatus
from app.rules.matrix import ExpectedEvidenceMatrix
from app.rules.negative_space import NegativeSpaceEvaluators


def test_neg01_silence_threshold_boundaries():
    """Test NEG-01 boundary conditions: 47.9h vs 48.1h silence."""
    now = datetime.now(timezone.utc)
    cse = CSE(id=uuid.uuid4(), name="Boundary CSE", sector="ENERGY", entity_type="UTILITY", size_tier="TIER_1")
    asset = Asset(
        id=uuid.uuid4(),
        cse_id=cse.id,
        name="Critical-Node-1",
        asset_type="SCADA_CONTROLLER",
        criticality=AssetCriticality.CRITICAL,
        status="ACTIVE"
    )

    # 1. Silence of 47.9h (just below default 48h threshold) -> PASS
    alert_47_9h = [Alert(
        id=uuid.uuid4(),
        cse_id=cse.id,
        asset_id=asset.id,
        source_system="SIEM",
        category="MALWARE_DETECTION",
        severity=AlertSeverity.HIGH,
        created_at=now - timedelta(hours=47.9)
    )]
    res_47_9h = NegativeSpaceEvaluators.evaluate_neg01_missing_telemetry(
        asset=asset, recent_alerts=alert_47_9h, maintenance_logs=[], evaluation_timestamp=now
    )
    assert res_47_9h.status == EvaluationStatus.PASS

    # 2. Silence of 48.1h (above default 48h threshold) -> CONFIRMED
    alert_48_1h = [Alert(
        id=uuid.uuid4(),
        cse_id=cse.id,
        asset_id=asset.id,
        source_system="SIEM",
        category="MALWARE_DETECTION",
        severity=AlertSeverity.HIGH,
        created_at=now - timedelta(hours=48.1)
    )]
    res_48_1h = NegativeSpaceEvaluators.evaluate_neg01_missing_telemetry(
        asset=asset, recent_alerts=alert_48_1h, maintenance_logs=[], evaluation_timestamp=now
    )
    assert res_48_1h.status == EvaluationStatus.CONFIRMED


def test_neg02_drop_threshold_boundaries_and_zero_variance():
    """Test NEG-02 drop ratio boundary conditions and safe zero-variance Z-score fallback."""
    now = datetime.now(timezone.utc)
    cse = CSE(id=uuid.uuid4(), name="Zero Variance CSE", sector="ENERGY", entity_type="UTILITY", size_tier="TIER_1")

    # 1. Zero Variance Baseline: Constant 10 alerts/day for past 30 days (days 0..29 baseline bin offsets)
    cutoff_baseline = now - timedelta(days=30)
    alerts_zero_var = []
    for day_idx in range(30):
        bin_time = cutoff_baseline + timedelta(days=day_idx, hours=12)
        if bin_time < (now - timedelta(hours=24)):  # Keep recent 24h at 0 alerts
            for _ in range(10):
                alerts_zero_var.append(Alert(
                    id=uuid.uuid4(),
                    cse_id=cse.id,
                    source_system="SIEM",
                    category="MALWARE_DETECTION",
                    severity=AlertSeverity.HIGH,
                    created_at=bin_time
                ))

    # Recent 24h has 0 alerts (100% drop) -> Safe fallback Z-score, CONFIRMED
    res_zero_var = NegativeSpaceEvaluators.evaluate_neg02_telemetry_drop(cse=cse, alerts=alerts_zero_var, evaluation_timestamp=now)
    assert res_zero_var.status == EvaluationStatus.CONFIRMED
    assert res_zero_var.baseline["mean_daily_volume"] > 5.0

    # 2. Drop ratio below threshold: 50% drop (threshold 75%) -> PASS
    alerts_50pct_drop = list(alerts_zero_var)
    for _ in range(5):  # 5 alerts in last 24h vs ~10/day mean
        alerts_50pct_drop.append(Alert(
            id=uuid.uuid4(),
            cse_id=cse.id,
            source_system="SIEM",
            category="MALWARE_DETECTION",
            severity=AlertSeverity.HIGH,
            created_at=now - timedelta(hours=12)
        ))
    res_50pct = NegativeSpaceEvaluators.evaluate_neg02_telemetry_drop(cse=cse, alerts=alerts_50pct_drop, drop_threshold_pct=75.0, evaluation_timestamp=now)
    assert res_50pct.status == EvaluationStatus.PASS


def test_neg03_expected_category_boundaries():
    """Test NEG-03 expected vs non-expected alert category matrix boundaries."""
    now = datetime.now(timezone.utc)
    cse = CSE(id=uuid.uuid4(), name="Energy CSE", sector="ENERGY", entity_type="UTILITY", size_tier="TIER_1")
    matrix = ExpectedEvidenceMatrix()

    # 1. Category present in alerts -> PASS
    alerts = [Alert(
        id=uuid.uuid4(),
        cse_id=cse.id,
        source_system="SIEM",
        category="MALWARE_DETECTION",
        severity=AlertSeverity.HIGH,
        created_at=now - timedelta(days=1)
    )]
    res_present = NegativeSpaceEvaluators.evaluate_neg03_missing_category(
        cse=cse, alerts=alerts, expected_category="MALWARE_DETECTION", matrix=matrix
    )
    assert res_present.status == EvaluationStatus.PASS

    # 2. Required category absent from alerts -> CONFIRMED
    res_absent = NegativeSpaceEvaluators.evaluate_neg03_missing_category(
        cse=cse, alerts=alerts, expected_category="EXFILTRATION_SUSPICION", matrix=matrix
    )
    assert res_absent.status == EvaluationStatus.CONFIRMED

    # 3. Category NOT in matrix -> NOT_APPLICABLE
    res_not_app = NegativeSpaceEvaluators.evaluate_neg03_missing_category(
        cse=cse, alerts=alerts, expected_category="NON_EXISTENT_CATEGORY", matrix=matrix
    )
    assert res_not_app.status == EvaluationStatus.NOT_APPLICABLE


def test_neg04_peer_density_boundaries():
    """Test NEG-04 peer density ratio boundary conditions (0.25 vs 0.10)."""
    now = datetime.now(timezone.utc)
    cse = CSE(id=uuid.uuid4(), name="Peer CSE", sector="ENERGY", entity_type="UTILITY", size_tier="TIER_1")

    target_asset = Asset(id=uuid.uuid4(), cse_id=cse.id, name="Target-SCADA", asset_type="SCADA_CONTROLLER", criticality=AssetCriticality.CRITICAL, status="ACTIVE")
    p1 = Asset(id=uuid.uuid4(), cse_id=cse.id, name="Peer-1", asset_type="SCADA_CONTROLLER", criticality=AssetCriticality.CRITICAL, status="ACTIVE")
    p2 = Asset(id=uuid.uuid4(), cse_id=cse.id, name="Peer-2", asset_type="SCADA_CONTROLLER", criticality=AssetCriticality.CRITICAL, status="ACTIVE")
    p3 = Asset(id=uuid.uuid4(), cse_id=cse.id, name="Peer-3", asset_type="SCADA_CONTROLLER", criticality=AssetCriticality.CRITICAL, status="ACTIVE")
    all_assets = [target_asset, p1, p2, p3]

    # Peer median density: 100 alerts
    all_alerts = []
    for peer in [p1, p2, p3]:
        for _ in range(100):
            all_alerts.append(Alert(id=uuid.uuid4(), cse_id=cse.id, asset_id=peer.id, source_system="SIEM", category="MALWARE_DETECTION", severity=AlertSeverity.HIGH, created_at=now - timedelta(days=5)))

    # 1. Target density 25 alerts (25% of peer median > 20% threshold) -> PASS
    alerts_25pct = list(all_alerts)
    for _ in range(25):
        alerts_25pct.append(Alert(id=uuid.uuid4(), cse_id=cse.id, asset_id=target_asset.id, source_system="SIEM", category="MALWARE_DETECTION", severity=AlertSeverity.HIGH, created_at=now - timedelta(days=5)))

    res_pass = NegativeSpaceEvaluators.evaluate_neg04_under_monitored_asset(
        target_asset=target_asset, all_assets=all_assets, all_alerts=alerts_25pct, under_monitored_ratio_threshold=0.20
    )
    assert res_pass.status == EvaluationStatus.PASS

    # 2. Target density 10 alerts (10% of peer median < 20% threshold) -> CONFIRMED
    alerts_10pct = list(all_alerts)
    for _ in range(10):
        alerts_10pct.append(Alert(id=uuid.uuid4(), cse_id=cse.id, asset_id=target_asset.id, source_system="SIEM", category="MALWARE_DETECTION", severity=AlertSeverity.HIGH, created_at=now - timedelta(days=5)))

    res_confirmed = NegativeSpaceEvaluators.evaluate_neg04_under_monitored_asset(
        target_asset=target_asset, all_assets=all_assets, all_alerts=alerts_10pct, under_monitored_ratio_threshold=0.20
    )
    assert res_confirmed.status == EvaluationStatus.CONFIRMED


def test_neg05_maintenance_context_boundaries():
    """Test NEG-05 maintenance overlap, no overlap, and unannounced silence."""
    now = datetime.now(timezone.utc)
    cse = CSE(id=uuid.uuid4(), name="Maint CSE", sector="ENERGY", entity_type="UTILITY", size_tier="TIER_1")
    asset = Asset(id=uuid.uuid4(), cse_id=cse.id, name="Maint-Asset", asset_type="SCADA_CONTROLLER", criticality=AssetCriticality.CRITICAL, status="ACTIVE")

    # Historical alerts 10 days ago (silence for past 10 days)
    old_alerts = [Alert(id=uuid.uuid4(), cse_id=cse.id, asset_id=asset.id, source_system="SIEM", category="MALWARE_DETECTION", severity=AlertSeverity.HIGH, created_at=now - timedelta(days=10))]

    # 1. Overlapping authorized maintenance -> SUPPRESSED
    maint_log = MaintenanceLog(
        id=uuid.uuid4(), cse_id=cse.id, asset_id=asset.id, reason="Turbine upgrade",
        start_time=now - timedelta(days=9), end_time=now + timedelta(days=1)
    )
    res_maint = NegativeSpaceEvaluators.evaluate_neg05_unexplained_maintenance_silence(
        asset=asset, recent_alerts=old_alerts, maintenance_logs=[maint_log], evaluation_timestamp=now
    )
    assert res_maint.status == EvaluationStatus.SUPPRESSED

    # 2. Silence WITHOUT maintenance log -> CONFIRMED (MAINTENANCE_NOT_RECORDED)
    res_no_log = NegativeSpaceEvaluators.evaluate_neg05_unexplained_maintenance_silence(
        asset=asset, recent_alerts=old_alerts, maintenance_logs=[], evaluation_timestamp=now
    )
    assert res_no_log.status == EvaluationStatus.CONFIRMED
    assert "MAINTENANCE_NOT_RECORDED" in res_no_log.explanation
