from dataclasses import dataclass, asdict
from typing import List, Dict, Any


@dataclass
class QualityMetrics:
    total_records: int = 0
    accepted_records: int = 0
    quarantined_records: int = 0
    completeness_pct: float = 100.0
    timestamp_validity_pct: float = 100.0
    asset_mapping_pct: float = 100.0
    cse_mapping_pct: float = 100.0
    duplicate_rate_pct: float = 0.0
    invalid_record_rate_pct: float = 0.0
    missing_investigation_pct: float = 0.0
    missing_escalation_pct: float = 0.0
    overall_quality_score: float = 100.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class DataQualityAssessor:
    """Evaluates dataset completeness and quality metrics, providing confidence modifiers for findings."""

    @staticmethod
    def compute_metrics(
        total_records: int,
        accepted_records: int,
        quarantined_records: int,
        invalid_timestamps: int = 0,
        unmapped_assets: int = 0,
        unmapped_cses: int = 0,
        duplicate_records: int = 0,
        uninvestigated_critical_alerts: int = 0,
        total_critical_alerts: int = 0
    ) -> QualityMetrics:
        if total_records == 0:
            return QualityMetrics()

        comp_pct = round((accepted_records / total_records) * 100.0, 2)
        ts_valid_pct = round(((total_records - invalid_timestamps) / total_records) * 100.0, 2)
        asset_map_pct = round(((total_records - unmapped_assets) / total_records) * 100.0, 2)
        cse_map_pct = round(((total_records - unmapped_cses) / total_records) * 100.0, 2)
        dup_rate = round((duplicate_records / total_records) * 100.0, 2)
        invalid_rate = round((quarantined_records / total_records) * 100.0, 2)
        
        missing_inv_pct = 0.0
        if total_critical_alerts > 0:
            missing_inv_pct = round((uninvestigated_critical_alerts / total_critical_alerts) * 100.0, 2)

        # Weighted overall data quality score
        overall = (
            comp_pct * 0.35 +
            ts_valid_pct * 0.25 +
            asset_map_pct * 0.20 +
            cse_map_pct * 0.20
        )
        overall = round(max(0.0, min(100.0, overall)), 2)

        return QualityMetrics(
            total_records=total_records,
            accepted_records=accepted_records,
            quarantined_records=quarantined_records,
            completeness_pct=comp_pct,
            timestamp_validity_pct=ts_valid_pct,
            asset_mapping_pct=asset_map_pct,
            cse_mapping_pct=cse_map_pct,
            duplicate_rate_pct=dup_rate,
            invalid_record_rate_pct=invalid_rate,
            missing_investigation_pct=missing_inv_pct,
            missing_escalation_pct=0.0,
            overall_quality_score=overall
        )

    @staticmethod
    def calculate_confidence_modifier(completeness_score: float) -> float:
        """Propagates dataset completeness into downstream finding confidence.
        
        If completeness_score == 100%, modifier is 1.0 (no reduction).
        If completeness_score < 70%, confidence is significantly downgraded.
        """
        if completeness_score >= 95.0:
            return 1.0
        elif completeness_score >= 80.0:
            return 0.85
        elif completeness_score >= 60.0:
            return 0.65
        else:
            return 0.40
