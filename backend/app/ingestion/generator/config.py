from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, Any


@dataclass
class GeneratorConfig:
    seed: int = 42
    num_cses: int = 20
    assets_per_cse_min: int = 15
    assets_per_cse_max: int = 35
    total_alerts: int = 15000
    
    # Date range for generated operational evidence
    start_date: datetime = field(default_factory=lambda: datetime(2026, 1, 1, tzinfo=timezone.utc))
    duration_days: int = 60
    
    # Scenario class ratios (sum to 1.0)
    scenario_ratios: Dict[str, float] = field(default_factory=lambda: {
        "NORMAL": 0.70,
        "EXECUTION_GAP": 0.12,
        "NEGATIVE_SPACE": 0.08,
        "PEER_ANOMALY": 0.04,
        "MIXED_SIGNAL": 0.03,
        "LEGITIMATE_EXCEPTION": 0.03
    })
    
    # Sector distributions for peer group formation
    sectors: list[str] = field(default_factory=lambda: ["ENERGY", "BANKING", "TELECOM", "DEFENCE", "HEALTHCARE"])
    size_tiers: list[str] = field(default_factory=lambda: ["TIER_1", "TIER_2", "TIER_3"])

    @classmethod
    def baseline_preset(cls) -> "GeneratorConfig":
        """Baseline size for fast, deterministic local development & testing (~15k alerts)."""
        return cls(
            seed=42,
            num_cses=20,
            assets_per_cse_min=15,
            assets_per_cse_max=30,
            total_alerts=15000,
            duration_days=60
        )

    @classmethod
    def scaleup_preset(cls) -> "GeneratorConfig":
        """Scale-up configuration for performance testing (~250k alerts across 40 CSEs)."""
        return cls(
            seed=2026,
            num_cses=40,
            assets_per_cse_min=50,
            assets_per_cse_max=100,
            total_alerts=250000,
            duration_days=90
        )
