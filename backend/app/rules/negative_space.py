import math
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
import numpy as np

from app.models import CSE, Asset, Alert, MaintenanceLog, AlertSeverity, AssetCriticality, FindingSeverity
from app.rules.evaluator import RuleEvaluationResult, EvaluationStatus
from app.rules.matrix import ExpectedEvidenceMatrix, ExpectedEvidenceRule
from app.ingestion.quality import DataQualityAssessor


class NegativeSpaceEvaluators:
    """Implementations of Negative Space rules (NEG-01 through NEG-05)

    Negative Space represents MISSING EXPECTED EVIDENCE, established by comparing
    expected operational activity against observed activity following context validation.
    """

    @staticmethod
    def evaluate_neg01_missing_telemetry(
        asset: Asset,
        recent_alerts: List[Alert],
        maintenance_logs: List[MaintenanceLog],
        matrix: Optional[ExpectedEvidenceMatrix] = None,
        completeness_score: float = 100.0,
        evaluation_timestamp: Optional[datetime] = None
    ) -> RuleEvaluationResult:
        """NEG-01: Expected Log Telemetry Missing for Active Critical Asset.

        Pipeline: Active critical asset -> Expected window -> Observed activity -> Silence > threshold -> Context validation -> Finding if justified.
        """
        matrix = matrix or ExpectedEvidenceMatrix()
        now = evaluation_timestamp or datetime.now(timezone.utc)

        # 1. Applicability: Must be CRITICAL Asset
        if asset.criticality != AssetCriticality.CRITICAL:
            return RuleEvaluationResult(
                rule_id="NEG-01",
                rule_version="1.0.0",
                target_entity_id=str(asset.id),
                target_entity_type="Asset",
                status=EvaluationStatus.NOT_APPLICABLE,
                applicability=False,
                expectation="Active critical asset expected to produce continuous telemetry.",
                observed_activity=f"Asset {asset.name} is status={asset.status}, criticality={asset.criticality.value}.",
                severity=FindingSeverity.HIGH,
                confidence=1.0,
                risk_contribution=0.0,
                evidence_refs=[],
                explanation="Rule applies only to CRITICAL assets.",
                recommendation=""
            )

        # 2. Dataset Completeness check (<50% -> UNKNOWN)
        if completeness_score < 50.0:
            return RuleEvaluationResult(
                rule_id="NEG-01",
                rule_version="1.0.0",
                target_entity_id=str(asset.id),
                target_entity_type="Asset",
                status=EvaluationStatus.UNKNOWN,
                applicability=True,
                expectation="Telemetry expected for active critical asset.",
                observed_activity="Dataset completeness below 50%; missing telemetry cannot be distinguished from export truncation.",
                severity=FindingSeverity.HIGH,
                confidence=0.40,
                risk_contribution=0.0,
                evidence_refs=[],
                explanation="Incomplete dataset export.",
                recommendation="Re-export complete dataset."
            )

        # 3. Context Validation: Check Decommissioned & Maintenance Exceptions
        if asset.status == "DECOMMISSIONED" or asset.decommissioned_at is not None:
            return RuleEvaluationResult(
                rule_id="NEG-01",
                rule_version="1.0.0",
                target_entity_id=str(asset.id),
                target_entity_type="Asset",
                status=EvaluationStatus.SUPPRESSED,
                applicability=True,
                expectation="Continuous telemetry unless decommissioned.",
                observed_activity=f"Asset {asset.name} is decommissioned.",
                severity=FindingSeverity.LOW,
                confidence=0.95,
                risk_contribution=0.0,
                evidence_refs=[{"source_table": "assets", "source_record_id": str(asset.id), "description": f"Decommissioned asset {asset.name}"}],
                explanation="Telemetry silence justified by decommissioned status.",
                recommendation=""
            )

        if maintenance_logs:
            return RuleEvaluationResult(
                rule_id="NEG-01",
                rule_version="1.0.0",
                target_entity_id=str(asset.id),
                target_entity_type="Asset",
                status=EvaluationStatus.SUPPRESSED,
                applicability=True,
                expectation="Telemetry required unless scheduled maintenance active.",
                observed_activity=f"Asset {asset.name} telemetry silence during recorded maintenance window.",
                severity=FindingSeverity.LOW,
                confidence=0.95,
                risk_contribution=0.0,
                evidence_refs=[{"source_table": "maintenance_logs", "source_record_id": str(m.id), "description": f"Maintenance window: {m.reason}"} for m in maintenance_logs],
                explanation="Telemetry silence justified by recorded maintenance log.",
                recommendation=""
            )

        # 4. Threshold & Observation Calculation
        threshold_hours = matrix.get_telemetry_window_hours(asset)
        asset_alerts = [a for a in recent_alerts if a.asset_id == asset.id]
        
        last_observed_time = max([a.created_at for a in asset_alerts]) if asset_alerts else None
        if last_observed_time and last_observed_time.tzinfo is None:
            last_observed_time = last_observed_time.replace(tzinfo=timezone.utc)

        silence_hours = (now - last_observed_time).total_seconds() / 3600.0 if last_observed_time else threshold_hours + 1.0

        if silence_hours >= threshold_hours:
            conf_mod = DataQualityAssessor.calculate_confidence_modifier(completeness_score)
            evidence = [{"source_table": "assets", "source_record_id": str(asset.id), "description": f"Critical Asset {asset.name} (Type: {asset.asset_type}, Status: ACTIVE, Decommissioned: NO, Maintenance: NONE)"}]
            if last_observed_time:
                evidence.append({"source_table": "alerts", "source_record_id": str(asset_alerts[0].id), "description": f"Last activity observed at {last_observed_time.isoformat()}"})

            return RuleEvaluationResult(
                rule_id="NEG-01",
                rule_version="1.0.0",
                target_entity_id=str(asset.id),
                target_entity_type="Asset",
                status=EvaluationStatus.CONFIRMED,
                applicability=True,
                expectation=f"Active critical asset {asset.name} expected to generate telemetry at least every {threshold_hours}h.",
                expected_behaviour=f"Continuous telemetry expected within {threshold_hours}h window.",
                observed_behaviour=f"Telemetry silence of {round(silence_hours, 1)}h exceeds threshold {threshold_hours}h.",
                expected_window=f"{threshold_hours}h",
                observed_window=f"{round(silence_hours, 1)}h",
                expected_activity=f">= 1 observation / {threshold_hours}h",
                observed_activity=f"0 observations in last {round(silence_hours, 1)}h",
                absence_deviation_measurement=f"Silence duration: {round(silence_hours, 1)}h",
                baseline={"threshold_hours": threshold_hours, "expected_min_count": 1},
                context_checks={"active_status": asset.status, "maintenance": "NONE", "decommissioned": False, "completeness_score": completeness_score},
                data_quality={"completeness_score": completeness_score, "confidence_modifier": conf_mod},
                severity=FindingSeverity.HIGH,
                confidence=round(0.95 * conf_mod, 2),
                risk_contribution=25.0,
                evidence_refs=evidence,
                explanation=f"Complete telemetry silence ({round(silence_hours, 1)}h) detected on active Critical asset {asset.name} without an active maintenance record.",
                recommendation="Inspect SIEM log forwarding agent, network connectivity, and collector status."
            )

        return RuleEvaluationResult(
            rule_id="NEG-01",
            rule_version="1.0.0",
            target_entity_id=str(asset.id),
            target_entity_type="Asset",
            status=EvaluationStatus.PASS,
            applicability=True,
            expectation="Continuous telemetry expected.",
            observed_activity=f"Observed {len(asset_alerts)} telemetry/alert records within expected window.",
            severity=FindingSeverity.HIGH,
            confidence=1.0,
            risk_contribution=0.0,
            evidence_refs=[],
            explanation="Telemetry active and within normal threshold.",
            recommendation=""
        )

    @staticmethod
    def evaluate_neg02_telemetry_drop(
        cse: CSE,
        alerts: List[Alert],
        maintenance_logs: List[MaintenanceLog] = None,
        completeness_score: float = 100.0,
        drop_threshold_pct: float = 70.0,
        rolling_baseline_days: int = 30,
        evaluation_timestamp: Optional[datetime] = None
    ) -> RuleEvaluationResult:
        """NEG-02: Sudden Telemetry/Activity Drop (Rolling 30-day Time-Series Baseline).

        Calculates rolling daily baseline (mean, std dev) over past 30 days and compares against recent 24h volume.
        """
        now = evaluation_timestamp or datetime.now(timezone.utc)
        
        # 1. Dataset Completeness check (<50% -> UNKNOWN)
        if completeness_score < 50.0:
            return RuleEvaluationResult(
                rule_id="NEG-02",
                rule_version="1.0.0",
                target_entity_id=str(cse.id),
                target_entity_type="CSE",
                status=EvaluationStatus.UNKNOWN,
                applicability=True,
                expectation="Normal baseline telemetry expected.",
                observed_activity="Dataset completeness < 50%; volume reduction may be artifact of data export truncation.",
                severity=FindingSeverity.CRITICAL,
                confidence=0.40,
                risk_contribution=0.0,
                evidence_refs=[],
                explanation="Incomplete dataset export.",
                recommendation="Re-export complete dataset."
            )

        # 2. Context Validation: CSE-wide Maintenance
        if maintenance_logs:
            return RuleEvaluationResult(
                rule_id="NEG-02",
                rule_version="1.0.0",
                target_entity_id=str(cse.id),
                target_entity_type="CSE",
                status=EvaluationStatus.SUPPRESSED,
                applicability=True,
                expectation="Consistent telemetry volume unless entity-wide maintenance window.",
                observed_activity=f"Telemetry drop across CSE {cse.name} explained by recorded maintenance window.",
                severity=FindingSeverity.LOW,
                confidence=0.95,
                risk_contribution=0.0,
                evidence_refs=[{"source_table": "maintenance_logs", "source_record_id": str(m.id), "description": f"CSE maintenance: {m.reason}"} for m in maintenance_logs],
                explanation="Telemetry volume reduction suppressed due to authorized maintenance.",
                recommendation=""
            )

        # 3. Time-Series Baseline Calculation
        cse_alerts = [a for a in alerts if a.cse_id == cse.id]
        if not cse_alerts:
            # Zero alerts overall
            conf_mod = DataQualityAssessor.calculate_confidence_modifier(completeness_score)
            return RuleEvaluationResult(
                rule_id="NEG-02",
                rule_version="1.0.0",
                target_entity_id=str(cse.id),
                target_entity_type="CSE",
                status=EvaluationStatus.CONFIRMED,
                applicability=True,
                expectation=f"CSE {cse.name} expected to maintain consistent daily telemetry volume.",
                expected_behaviour="Continuous daily telemetry volume.",
                observed_behaviour=f"Zero alerts ingested across entire CSE {cse.name} over baseline period.",
                expected_window="30d rolling",
                observed_window="24h recent",
                expected_activity="Baseline telemetry volume",
                observed_activity="0 alerts",
                absence_deviation_measurement="100% telemetry drop",
                baseline={"baseline_mean_daily": 0.0, "baseline_std_dev": 0.0},
                context_checks={"maintenance": "NONE", "completeness_score": completeness_score},
                data_quality={"completeness_score": completeness_score, "confidence_modifier": conf_mod},
                severity=FindingSeverity.CRITICAL,
                confidence=round(0.95 * conf_mod, 2),
                risk_contribution=30.0,
                evidence_refs=[{"source_table": "cses", "source_record_id": str(cse.id), "description": f"CSE {cse.name} (Tier: {cse.size_tier.value if hasattr(cse.size_tier, 'value') else str(cse.size_tier)})"}],
                explanation=f"Entity-wide 100% telemetry blackout detected for CSE {cse.name}.",
                recommendation="Audit SOC ingestion pipeline and syslog listeners."
            )

        # Group alerts into daily bins over past 30 days
        cutoff_baseline = now - timedelta(days=rolling_baseline_days)
        cutoff_recent = now - timedelta(hours=24)

        daily_counts = {}
        for day_idx in range(rolling_baseline_days):
            day_start = cutoff_baseline + timedelta(days=day_idx)
            daily_counts[day_idx] = 0

        recent_count = 0
        baseline_counts = []

        for a in cse_alerts:
            ts = a.created_at
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= cutoff_recent:
                recent_count += 1
            if ts >= cutoff_baseline:
                day_idx = int((ts - cutoff_baseline).total_seconds() // 86400)
                if day_idx in daily_counts:
                    daily_counts[day_idx] += 1

        baseline_values = list(daily_counts.values())
        if len(baseline_values) < 7:
            return RuleEvaluationResult(
                rule_id="NEG-02",
                rule_version="1.0.0",
                target_entity_id=str(cse.id),
                target_entity_type="CSE",
                status=EvaluationStatus.INSUFFICIENT_DATA,
                applicability=True,
                expectation="Rolling 30-day baseline calculation.",
                observed_activity=f"Fewer than 7 days of historical baseline available ({len(baseline_values)} days).",
                severity=FindingSeverity.LOW,
                confidence=0.50,
                risk_contribution=0.0,
                evidence_refs=[],
                explanation="Insufficient baseline history to reliably compute telemetry drop deviation.",
                recommendation=""
            )

        mean_vol = float(np.mean(baseline_values))
        raw_std_vol = float(np.std(baseline_values))

        if mean_vol > 0:
            reduction_pct = round(((mean_vol - recent_count) / mean_vol) * 100.0, 2)
            # Safe deterministic fallback for zero or near-zero variance historical baselines
            if raw_std_vol < 1e-6:
                effective_std = max(raw_std_vol, 0.10 * mean_vol)
            else:
                effective_std = raw_std_vol
            z_score = round((mean_vol - recent_count) / effective_std, 2)
            std_vol = raw_std_vol
        else:
            reduction_pct = 0.0
            z_score = 0.0
            std_vol = 0.0

        if reduction_pct >= drop_threshold_pct and z_score >= 1.5:
            conf_mod = DataQualityAssessor.calculate_confidence_modifier(completeness_score)
            return RuleEvaluationResult(
                rule_id="NEG-02",
                rule_version="1.0.0",
                target_entity_id=str(cse.id),
                target_entity_type="CSE",
                status=EvaluationStatus.CONFIRMED,
                applicability=True,
                expectation=f"CSE {cse.name} daily telemetry expected around baseline mean {round(mean_vol, 1)} events/day.",
                expected_behaviour=f"Consistent daily alert volume (baseline mean {round(mean_vol, 1)} events/day).",
                observed_behaviour=f"Recent 24h volume dropped to {recent_count} events ({reduction_pct}% drop, Z={z_score}).",
                expected_window=f"{rolling_baseline_days}d baseline",
                observed_window="24h recent",
                expected_activity=f"~{round(mean_vol, 1)} alerts / day",
                observed_activity=f"{recent_count} alerts in last 24h",
                absence_deviation_measurement=f"{reduction_pct}% drop below mean (Z-score = {z_score})",
                baseline={"mean_daily_volume": round(mean_vol, 2), "std_dev": round(std_vol, 2), "rolling_days": rolling_baseline_days},
                context_checks={"maintenance": "NONE", "completeness_score": completeness_score},
                data_quality={"completeness_score": completeness_score, "confidence_modifier": conf_mod},
                severity=FindingSeverity.CRITICAL,
                confidence=round(0.95 * conf_mod, 2),
                risk_contribution=30.0,
                evidence_refs=[{"source_table": "cses", "source_record_id": str(cse.id), "description": f"CSE {cse.name} baseline daily mean: {round(mean_vol, 1)}, recent 24h: {recent_count}"}],
                explanation=f"Sudden {reduction_pct}% drop in telemetry volume detected for CSE {cse.name} compared to rolling {rolling_baseline_days}-day baseline (Z-score: {z_score}).",
                recommendation="Investigate SIEM log forwarders, firewall rules, and ingestion pipeline status."
            )

        return RuleEvaluationResult(
            rule_id="NEG-02",
            rule_version="1.0.0",
            target_entity_id=str(cse.id),
            target_entity_type="CSE",
            status=EvaluationStatus.PASS,
            applicability=True,
            expectation="Stable daily telemetry volume.",
            observed_activity=f"Recent 24h volume ({recent_count}) within normal baseline range (mean {round(mean_vol, 1)}).",
            severity=FindingSeverity.CRITICAL,
            confidence=1.0,
            risk_contribution=0.0,
            evidence_refs=[],
            explanation="Telemetry volume normal.",
            recommendation=""
        )

    @staticmethod
    def evaluate_neg03_missing_category(
        cse: CSE,
        alerts: List[Alert],
        expected_category: str = "MALWARE_DETECTION",
        matrix: Optional[ExpectedEvidenceMatrix] = None,
        completeness_score: float = 100.0
    ) -> RuleEvaluationResult:
        """NEG-03: Missing Expected High-Risk Alert Category.

        Uses ExpectedEvidenceMatrix to determine applicability.
        """
        matrix = matrix or ExpectedEvidenceMatrix()

        # 1. Applicability Check via ExpectedEvidenceMatrix
        if not matrix.is_category_expected_for_cse(cse, expected_category):
            return RuleEvaluationResult(
                rule_id="NEG-03",
                rule_version="1.0.0",
                target_entity_id=str(cse.id),
                target_entity_type="CSE",
                status=EvaluationStatus.NOT_APPLICABLE,
                applicability=False,
                expectation=f"Category {expected_category} evaluation.",
                observed_activity=f"Category {expected_category} is NOT applicable to CSE {cse.name} sector/tier.",
                severity=FindingSeverity.HIGH,
                confidence=1.0,
                risk_contribution=0.0,
                evidence_refs=[],
                explanation=f"Category {expected_category} not required for CSE tier {cse.size_tier.value if hasattr(cse.size_tier, 'value') else str(cse.size_tier)}.",
                recommendation=""
            )

        # 2. Dataset Completeness check (<50% -> UNKNOWN)
        if completeness_score < 50.0:
            return RuleEvaluationResult(
                rule_id="NEG-03",
                rule_version="1.0.0",
                target_entity_id=str(cse.id),
                target_entity_type="CSE",
                status=EvaluationStatus.UNKNOWN,
                applicability=True,
                expectation=f"Presence of high-risk category {expected_category}.",
                observed_activity="Dataset completeness < 50%; category absence may be due to incomplete export.",
                severity=FindingSeverity.HIGH,
                confidence=0.40,
                risk_contribution=0.0,
                evidence_refs=[],
                explanation="Incomplete dataset export.",
                recommendation="Re-export complete dataset."
            )

        # 3. Observation Check
        cse_alerts = [a for a in alerts if a.cse_id == cse.id]
        categories_present = {a.category for a in cse_alerts}

        if expected_category not in categories_present:
            conf_mod = DataQualityAssessor.calculate_confidence_modifier(completeness_score)
            return RuleEvaluationResult(
                rule_id="NEG-03",
                rule_version="1.0.0",
                target_entity_id=str(cse.id),
                target_entity_type="CSE",
                status=EvaluationStatus.CONFIRMED,
                applicability=True,
                expectation=f"CSE {cse.name} expected to log {expected_category} events in baseline detection portfolio.",
                expected_behaviour=f"Expected telemetry category {expected_category} present in active detection feed.",
                observed_behaviour=f"Zero {expected_category} alerts recorded across CSE {cse.name} over evaluation window.",
                expected_window="30d",
                observed_window="30d",
                expected_activity=f">= 1 {expected_category} alert",
                observed_activity="0 alerts in expected category",
                absence_deviation_measurement=f"100% absence of expected category {expected_category}",
                baseline={"expected_category": expected_category},
                context_checks={"completeness_score": completeness_score},
                data_quality={"completeness_score": completeness_score, "confidence_modifier": conf_mod},
                severity=FindingSeverity.HIGH,
                confidence=round(0.90 * conf_mod, 2),
                risk_contribution=20.0,
                evidence_refs=[{"source_table": "cses", "source_record_id": str(cse.id), "description": f"CSE {cse.name} ({cse.sector.value if hasattr(cse.sector, 'value') else str(cse.sector)})"}],
                explanation=f"Complete absence of mandatory expected alert category {expected_category} for CSE {cse.name}.",
                recommendation=f"Review SIEM detection rule enablement and endpoint coverage for {expected_category}."
            )

        return RuleEvaluationResult(
            rule_id="NEG-03",
            rule_version="1.0.0",
            target_entity_id=str(cse.id),
            target_entity_type="CSE",
            status=EvaluationStatus.PASS,
            applicability=True,
            expectation=f"Presence of category {expected_category}.",
            observed_activity=f"Observed category {expected_category} in CSE alert feed.",
            severity=FindingSeverity.HIGH,
            confidence=1.0,
            risk_contribution=0.0,
            evidence_refs=[],
            explanation=f"Category {expected_category} active.",
            recommendation=""
        )

    @staticmethod
    def evaluate_neg04_under_monitored_asset(
        target_asset: Asset,
        all_assets: List[Asset],
        all_alerts: List[Alert],
        completeness_score: float = 100.0,
        under_monitored_ratio_threshold: float = 0.20
    ) -> RuleEvaluationResult:
        """NEG-04: Critical Asset Under-Monitoring vs Peer Group Baseline.

        Compares target asset alert/telemetry density against peer assets matching (asset_type, criticality).
        """
        # 1. Applicability Check: Must be CRITICAL or HIGH criticality asset
        if target_asset.criticality not in (AssetCriticality.CRITICAL, AssetCriticality.HIGH) or target_asset.status != "ACTIVE":
            return RuleEvaluationResult(
                rule_id="NEG-04",
                rule_version="1.0.0",
                target_entity_id=str(target_asset.id),
                target_entity_type="Asset",
                status=EvaluationStatus.NOT_APPLICABLE,
                applicability=False,
                expectation="Peer group monitoring density evaluation.",
                observed_activity=f"Asset {target_asset.name} is non-critical or inactive.",
                severity=FindingSeverity.MEDIUM,
                confidence=1.0,
                risk_contribution=0.0,
                evidence_refs=[],
                explanation="Rule applicable to active CRITICAL or HIGH criticality assets.",
                recommendation=""
            )

        # 2. Dataset Completeness check (<50% -> UNKNOWN)
        if completeness_score < 50.0:
            return RuleEvaluationResult(
                rule_id="NEG-04",
                rule_version="1.0.0",
                target_entity_id=str(target_asset.id),
                target_entity_type="Asset",
                status=EvaluationStatus.UNKNOWN,
                applicability=True,
                expectation="Peer baseline comparison.",
                observed_activity="Dataset completeness < 50%; peer density calculation unreliable.",
                severity=FindingSeverity.MEDIUM,
                confidence=0.40,
                risk_contribution=0.0,
                evidence_refs=[],
                explanation="Incomplete dataset export.",
                recommendation="Re-export complete dataset."
            )

        # 3. Select Peer Group (Matching asset_type and criticality)
        peer_assets = [
            a for a in all_assets
            if a.asset_type == target_asset.asset_type
            and a.criticality == target_asset.criticality
            and a.status == "ACTIVE"
            and a.id != target_asset.id
        ]

        if len(peer_assets) < 1:
            return RuleEvaluationResult(
                rule_id="NEG-04",
                rule_version="1.0.0",
                target_entity_id=str(target_asset.id),
                target_entity_type="Asset",
                status=EvaluationStatus.INSUFFICIENT_DATA,
                applicability=True,
                expectation="Peer group comparison.",
                observed_activity=f"No matching peer assets found for type {target_asset.asset_type} and criticality {target_asset.criticality.value}.",
                severity=FindingSeverity.MEDIUM,
                confidence=0.50,
                risk_contribution=0.0,
                evidence_refs=[],
                explanation="Insufficient peer assets to compute baseline density.",
                recommendation=""
            )

        # Calculate alert count for target and peers
        alerts_by_asset: Dict[str, int] = {}
        for alt in all_alerts:
            alerts_by_asset[str(alt.asset_id)] = alerts_by_asset.get(str(alt.asset_id), 0) + 1

        target_density = float(alerts_by_asset.get(str(target_asset.id), 0))
        peer_densities = [float(alerts_by_asset.get(str(p.id), 0)) for p in peer_assets]
        peer_median_density = float(np.median(peer_densities))

        if peer_median_density > 0:
            density_ratio = target_density / peer_median_density
        else:
            density_ratio = 1.0

        if density_ratio < under_monitored_ratio_threshold:
            conf_mod = DataQualityAssessor.calculate_confidence_modifier(completeness_score)
            return RuleEvaluationResult(
                rule_id="NEG-04",
                rule_version="1.0.0",
                target_entity_id=str(target_asset.id),
                target_entity_type="Asset",
                status=EvaluationStatus.CONFIRMED,
                applicability=True,
                expectation=f"Asset {target_asset.name} telemetry density should align with peer group median ({round(peer_median_density, 1)} events).",
                expected_behaviour=f"Telemetry density >= {round(under_monitored_ratio_threshold * 100)}% of peer median ({round(peer_median_density, 1)} events).",
                observed_behaviour=f"Actual density is {target_density} events ({round(density_ratio * 100, 1)}% of peer median).",
                expected_window="30d",
                observed_window="30d",
                expected_activity=f"Peer median density: {round(peer_median_density, 1)} events",
                observed_activity=f"Target density: {target_density} events",
                absence_deviation_measurement=f"Density is {round(density_ratio * 100, 1)}% of peer baseline (< {round(under_monitored_ratio_threshold * 100)}% threshold)",
                baseline={"peer_group_size": len(peer_assets), "peer_median_density": peer_median_density, "asset_type": target_asset.asset_type},
                context_checks={"completeness_score": completeness_score},
                data_quality={"completeness_score": completeness_score, "confidence_modifier": conf_mod},
                severity=FindingSeverity.MEDIUM,
                confidence=round(0.85 * conf_mod, 2),
                risk_contribution=15.0,
                evidence_refs=[
                    {"source_table": "assets", "source_record_id": str(target_asset.id), "description": f"Target Asset {target_asset.name} density: {target_density}"},
                    {"source_table": "assets", "source_record_id": "PEER_GROUP_BASELINE", "description": f"Peer Group ({len(peer_assets)} {target_asset.asset_type} nodes) median density: {peer_median_density}"}
                ],
                explanation=f"Critical asset {target_asset.name} is severely under-monitored, exhibiting only {round(density_ratio * 100, 1)}% of peer group telemetry density.",
                recommendation="Audit log collection agent configuration and sensor deployment on target asset."
            )

        return RuleEvaluationResult(
            rule_id="NEG-04",
            rule_version="1.0.0",
            target_entity_id=str(target_asset.id),
            target_entity_type="Asset",
            status=EvaluationStatus.PASS,
            applicability=True,
            expectation="Telemetry density aligns with peer group.",
            observed_activity=f"Target density ({target_density}) is {round(density_ratio * 100, 1)}% of peer median ({peer_median_density}).",
            severity=FindingSeverity.MEDIUM,
            confidence=1.0,
            risk_contribution=0.0,
            evidence_refs=[],
            explanation="Monitoring density within acceptable peer range.",
            recommendation=""
        )

    @staticmethod
    def evaluate_neg05_unexplained_maintenance_silence(
        asset: Asset,
        recent_alerts: List[Alert],
        maintenance_logs: List[MaintenanceLog],
        suspected_silence_window_hours: float = 24.0,
        completeness_score: float = 100.0,
        evaluation_timestamp: Optional[datetime] = None
    ) -> RuleEvaluationResult:
        """NEG-05: Unexplained Maintenance Silence.

        Detects temporal activity reduction overlapping a suspected maintenance window/operational change,
        and verifies whether an authorized MaintenanceLog record exists.

        States:
            MAINTENANCE_EXPLAINED -> SUPPRESSED
            MAINTENANCE_NOT_RECORDED -> CONFIRMED (Finding generated)
            NO_MAINTENANCE_CONTEXT -> PASS / NOT_APPLICABLE
            UNKNOWN -> UNKNOWN
        """
        now = evaluation_timestamp or datetime.now(timezone.utc)

        # 1. Dataset Completeness check (<50% -> UNKNOWN)
        if completeness_score < 50.0:
            return RuleEvaluationResult(
                rule_id="NEG-05",
                rule_version="1.0.0",
                target_entity_id=str(asset.id),
                target_entity_type="Asset",
                status=EvaluationStatus.UNKNOWN,
                applicability=True,
                expectation="Maintenance context verification.",
                observed_activity="Dataset completeness < 50%; maintenance verification inconclusive.",
                severity=FindingSeverity.HIGH,
                confidence=0.40,
                risk_contribution=0.0,
                evidence_refs=[],
                explanation="Incomplete dataset export.",
                recommendation="Re-export complete dataset."
            )

        # 2. Detect Activity Silence Window
        asset_alerts = [a for a in recent_alerts if a.asset_id == asset.id]
        last_observed = max([a.created_at for a in asset_alerts]) if asset_alerts else None
        if last_observed and last_observed.tzinfo is None:
            last_observed = last_observed.replace(tzinfo=timezone.utc)

        silence_hours = (now - last_observed).total_seconds() / 3600.0 if last_observed else suspected_silence_window_hours + 1.0

        if silence_hours < suspected_silence_window_hours:
            # NO_MAINTENANCE_CONTEXT / Normal activity
            return RuleEvaluationResult(
                rule_id="NEG-05",
                rule_version="1.0.0",
                target_entity_id=str(asset.id),
                target_entity_type="Asset",
                status=EvaluationStatus.PASS,
                applicability=True,
                expectation="Normal operational activity.",
                observed_activity=f"No unannounced silence detected ({round(silence_hours, 1)}h < {suspected_silence_window_hours}h threshold).",
                severity=FindingSeverity.HIGH,
                confidence=1.0,
                risk_contribution=0.0,
                evidence_refs=[],
                explanation="Operational activity active.",
                recommendation=""
            )

        # 3. Check for Authorized Maintenance Log matching asset
        matching_logs = [m for m in maintenance_logs if str(m.asset_id) == str(asset.id)]

        if matching_logs:
            # State: MAINTENANCE_EXPLAINED
            return RuleEvaluationResult(
                rule_id="NEG-05",
                rule_version="1.0.0",
                target_entity_id=str(asset.id),
                target_entity_type="Asset",
                status=EvaluationStatus.SUPPRESSED,
                applicability=True,
                expectation="Activity silence must be backed by an authorized maintenance record.",
                observed_activity=f"Silence duration of {round(silence_hours, 1)}h matches recorded maintenance window.",
                severity=FindingSeverity.LOW,
                confidence=0.95,
                risk_contribution=0.0,
                evidence_refs=[{"source_table": "maintenance_logs", "source_record_id": str(m.id), "description": f"Approved maintenance: {m.reason}"} for m in matching_logs],
                explanation="MAINTENANCE_EXPLAINED: Activity silence matches authorized maintenance log.",
                recommendation=""
            )
        else:
            # State: MAINTENANCE_NOT_RECORDED -> CONFIRMED Finding!
            conf_mod = DataQualityAssessor.calculate_confidence_modifier(completeness_score)
            return RuleEvaluationResult(
                rule_id="NEG-05",
                rule_version="1.0.0",
                target_entity_id=str(asset.id),
                target_entity_type="Asset",
                status=EvaluationStatus.CONFIRMED,
                applicability=True,
                expectation=f"Operational change or activity blackout on asset {asset.name} requires prior authorized MaintenanceLog entry.",
                expected_behaviour="Authorized maintenance record filed in DB prior to operational silence.",
                observed_behaviour=f"Telemetry blackout of {round(silence_hours, 1)}h detected with NO matching maintenance log in canonical records.",
                expected_window=f"{suspected_silence_window_hours}h window",
                observed_window=f"{round(silence_hours, 1)}h silence",
                expected_activity="Authorized MaintenanceLog record in DB",
                observed_activity="ZERO maintenance records found for asset",
                absence_deviation_measurement=f"Unexplained operational silence for {round(silence_hours, 1)}h",
                baseline={"maintenance_records_found": 0},
                context_checks={"active_status": asset.status, "decommissioned": False, "maintenance_log_count": 0, "completeness_score": completeness_score},
                data_quality={"completeness_score": completeness_score, "confidence_modifier": conf_mod},
                severity=FindingSeverity.HIGH,
                confidence=round(0.90 * conf_mod, 2),
                risk_contribution=25.0,
                evidence_refs=[{"source_table": "assets", "source_record_id": str(asset.id), "description": f"Asset {asset.name} unannounced silence for {round(silence_hours, 1)}h"}],
                explanation=f"MAINTENANCE_NOT_RECORDED: Operational activity silence detected on asset {asset.name} without a corresponding authorized maintenance record.",
                recommendation="Audit SOC change management records and verify if unannounced outage occurred."
            )
