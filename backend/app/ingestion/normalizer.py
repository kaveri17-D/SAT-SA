from datetime import datetime, timezone
import dateutil.parser
from typing import Optional, Any
from app.models import AlertSeverity, AssetCriticality, FindingSeverity, DispositionType

# Configurable Mapping Tables for Severities
SEVERITY_MAPPINGS = {
    "CRITICAL": AlertSeverity.CRITICAL,
    "CRIT": AlertSeverity.CRITICAL,
    "P1": AlertSeverity.CRITICAL,
    "SEV-1": AlertSeverity.CRITICAL,
    "SEV1": AlertSeverity.CRITICAL,
    "5": AlertSeverity.CRITICAL,

    "HIGH": AlertSeverity.HIGH,
    "P2": AlertSeverity.HIGH,
    "SEV-2": AlertSeverity.HIGH,
    "SEV2": AlertSeverity.HIGH,
    "4": AlertSeverity.HIGH,

    "MEDIUM": AlertSeverity.MEDIUM,
    "MED": AlertSeverity.MEDIUM,
    "P3": AlertSeverity.MEDIUM,
    "SEV-3": AlertSeverity.MEDIUM,
    "SEV3": AlertSeverity.MEDIUM,
    "3": AlertSeverity.MEDIUM,

    "LOW": AlertSeverity.LOW,
    "P4": AlertSeverity.LOW,
    "SEV-4": AlertSeverity.LOW,
    "SEV4": AlertSeverity.LOW,
    "2": AlertSeverity.LOW,

    "INFO": AlertSeverity.INFO,
    "INFORMATIONAL": AlertSeverity.INFO,
    "P5": AlertSeverity.INFO,
    "SEV-5": AlertSeverity.INFO,
    "1": AlertSeverity.INFO,
}

CRITICALITY_MAPPINGS = {
    "CRITICAL": AssetCriticality.CRITICAL,
    "HIGH": AssetCriticality.HIGH,
    "MEDIUM": AssetCriticality.MEDIUM,
    "LOW": AssetCriticality.LOW,
    "TIER_1": AssetCriticality.CRITICAL,
    "TIER_2": AssetCriticality.HIGH,
    "TIER_3": AssetCriticality.MEDIUM,
}


class DataNormalizer:
    """Configurable normalization layer for operational evidence records."""

    @staticmethod
    def normalize_severity(raw_val: Any) -> AlertSeverity:
        if not raw_val:
            return AlertSeverity.MEDIUM
        val_str = str(raw_val).strip().upper()
        return SEVERITY_MAPPINGS.get(val_str, AlertSeverity.MEDIUM)

    @staticmethod
    def normalize_criticality(raw_val: Any) -> AssetCriticality:
        if not raw_val:
            return AssetCriticality.MEDIUM
        val_str = str(raw_val).strip().upper()
        return CRITICALITY_MAPPINGS.get(val_str, AssetCriticality.MEDIUM)

    @staticmethod
    def normalize_timestamp(raw_val: Any) -> Optional[datetime]:
        if not raw_val or str(raw_val).strip() == "":
            return None
        if isinstance(raw_val, datetime):
            if raw_val.tzinfo is None:
                return raw_val.replace(tzinfo=timezone.utc)
            return raw_val
        try:
            parsed = dateutil.parser.parse(str(raw_val))
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except (ValueError, TypeError):
            return None

    @staticmethod
    def normalize_disposition(raw_val: Any) -> DispositionType:
        if not raw_val:
            return DispositionType.INCONCLUSIVE
        val_str = str(raw_val).strip().upper()
        if "TRUE" in val_str or "POSITIVE" in val_str:
            return DispositionType.TRUE_POSITIVE
        elif "FALSE" in val_str:
            return DispositionType.FALSE_POSITIVE
        elif "BENIGN" in val_str:
            return DispositionType.BENIGN_POSITIVE
        elif "DUP" in val_str:
            return DispositionType.DUPLICATE
        return DispositionType.INCONCLUSIVE
