from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from app.models import AssetCriticality, CSE


@dataclass
class ExpectedEvidenceRule:
    """Configurable rule defining expected operational evidence for an asset or CSE."""
    rule_name: str
    asset_type: Optional[str] = None
    criticality: Optional[AssetCriticality] = None
    cse_sector: Optional[str] = None
    cse_size_tier: Optional[str] = None
    expected_category: Optional[str] = None
    expected_frequency_per_day: float = 1.0
    observation_window_hours: float = 48.0
    min_data_quality_completeness: float = 50.0
    is_applicable: bool = True


DEFAULT_EXPECTATION_RULES: List[ExpectedEvidenceRule] = [
    # Telemetry expectation rule for Critical SCADA / Controllers / Servers
    ExpectedEvidenceRule(
        rule_name="CRITICAL_ASSET_TELEMETRY_EXPECTATION",
        asset_type=None,
        criticality=AssetCriticality.CRITICAL,
        observation_window_hours=48.0,
        expected_frequency_per_day=0.5,
        min_data_quality_completeness=50.0,
        is_applicable=True
    ),
    # Expected High-Risk Security Category Rules
    ExpectedEvidenceRule(
        rule_name="EXPECT_MALWARE_DETECTION",
        expected_category="MALWARE_DETECTION",
        observation_window_hours=720.0,  # 30 days
        min_data_quality_completeness=50.0,
        is_applicable=True
    ),
    ExpectedEvidenceRule(
        rule_name="EXPECT_AUTHENTICATION_FAILURE",
        expected_category="AUTHENTICATION_FAILURE",
        observation_window_hours=720.0,
        min_data_quality_completeness=50.0,
        is_applicable=True
    ),
    ExpectedEvidenceRule(
        rule_name="EXPECT_PRIVILEGE_ESCALATION",
        expected_category="PRIVILEGE_ESCALATION",
        observation_window_hours=720.0,
        min_data_quality_completeness=50.0,
        is_applicable=True
    ),
    ExpectedEvidenceRule(
        rule_name="EXPECT_EXFILTRATION_SUSPICION",
        expected_category="EXFILTRATION_SUSPICION",
        observation_window_hours=720.0,
        min_data_quality_completeness=50.0,
        is_applicable=True
    ),
]


class ExpectedEvidenceMatrix:
    """Configurable service providing operational expectation matrix lookup."""

    def __init__(self, rules: Optional[List[ExpectedEvidenceRule]] = None):
        self.rules = rules if rules is not None else DEFAULT_EXPECTATION_RULES

    def get_telemetry_window_hours(self, asset: Any) -> float:
        """Get expected telemetry observation window in hours for an asset."""
        for rule in self.rules:
            if rule.rule_name == "CRITICAL_ASSET_TELEMETRY_EXPECTATION":
                if rule.criticality is None or asset.criticality == rule.criticality:
                    if rule.asset_type is None or asset.asset_type == rule.asset_type:
                        return rule.observation_window_hours
        return 48.0  # Default 48 hours threshold

    def get_expected_categories_for_cse(self, cse: CSE) -> List[str]:
        """Get list of high-risk security categories expected to be observed for a CSE."""
        expected = []
        sector_str = cse.sector.value if hasattr(cse.sector, 'value') else str(cse.sector)
        tier_str = cse.size_tier.value if hasattr(cse.size_tier, 'value') else str(cse.size_tier)
        for rule in self.rules:
            if rule.expected_category and rule.is_applicable:
                # Check CSE sector or size tier matching if specified
                if rule.cse_sector and sector_str != rule.cse_sector:
                    continue
                if rule.cse_size_tier and tier_str != rule.cse_size_tier:
                    continue
                expected.append(rule.expected_category)
        return expected

    def is_category_expected_for_cse(self, cse: CSE, category: str) -> bool:
        """Check if a specific alert category is expected for a CSE."""
        return category in self.get_expected_categories_for_cse(cse)

    def get_rule_for_category(self, cse: CSE, category: str) -> Optional[ExpectedEvidenceRule]:
        """Fetch expectation rule for a specific CSE and category combination."""
        sector_str = cse.sector.value if hasattr(cse.sector, 'value') else str(cse.sector)
        tier_str = cse.size_tier.value if hasattr(cse.size_tier, 'value') else str(cse.size_tier)
        for rule in self.rules:
            if rule.expected_category == category and rule.is_applicable:
                if rule.cse_sector and sector_str != rule.cse_sector:
                    continue
                if rule.cse_size_tier and tier_str != rule.cse_size_tier:
                    continue
                return rule
        return None
