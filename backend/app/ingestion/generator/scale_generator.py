import csv
import json
import os
import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Iterator


class ScaleDatasetGenerator:
    """Streams large-scale realistic SOC telemetry across controlled tiers without memory blow-up."""

    def __init__(
        self,
        seed: int = 42,
        num_cses: int = 20,
        num_assets_per_cse: int = 25,
        start_date: datetime = None,
        duration_days: int = 30
    ):
        self.rng = random.Random(seed)
        self.num_cses = num_cses
        self.num_assets_per_cse = num_assets_per_cse
        self.start_date = start_date or datetime(2026, 3, 1, tzinfo=timezone.utc)
        self.duration_days = duration_days
        self.end_date = self.start_date + timedelta(days=duration_days)

        self.categories = [
            "FIREWALL_DROP", "AUTH_FAILURE", "MALWARE_DETECTED", "EDR_SUSPICIOUS_PROC",
            "DNS_TUNNEL_ANOMALY", "DATA_EXFILTRATION", "PRIVILEGE_ESCALATION", "SIEM_RULE_MATCH"
        ]
        self.severities = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        self.severity_weights = [0.60, 0.25, 0.12, 0.03]  # realistic long-tail

    def generate_entities(self) -> Dict[str, Any]:
        cses = []
        assets = []
        analysts = []

        sectors = ["FINANCIAL", "ENERGY", "TELECOM", "HEALTHCARE", "DEFENSE", "TRANSPORT"]

        for i in range(1, self.num_cses + 1):
            cse_id = str(uuid.uuid4())
            cse_name = f"CSE_{sectors[(i-1) % len(sectors)]}_{i:02d}"
            cses.append({
                "id": cse_id,
                "name": cse_name,
                "sector": sectors[(i-1) % len(sectors)],
                "criticality": "CRITICAL" if i <= 5 else "HIGH",
                "tier": "TIER_1" if i <= 5 else "TIER_2",
                "created_at": self.start_date.isoformat()
            })

            # Generate assets for this CSE
            for j in range(1, self.num_assets_per_cse + 1):
                asset_id = str(uuid.uuid4())
                assets.append({
                    "id": asset_id,
                    "cse_id": cse_id,
                    "name": f"{cse_name}_SRV_{j:02d}",
                    "asset_type": "SERVER" if j <= 15 else "DATABASE",
                    "criticality": "CRITICAL" if j <= 5 else ("HIGH" if j <= 15 else "MEDIUM"),
                    "ip_address": f"10.{i}.{j // 256}.{j % 256 + 1}",
                    "is_active": True,
                    "created_at": self.start_date.isoformat()
                })

            # Analysts for this CSE
            for k in range(1, 6):
                analysts.append({
                    "id": str(uuid.uuid4()),
                    "cse_id": cse_id,
                    "name": f"Analyst_{i:02d}_{k:02d}",
                    "role": "TIER_1_ANALYST" if k <= 3 else "SENIOR_LEAD",
                    "shift": "DAY" if k % 2 == 1 else "NIGHT",
                    "created_at": self.start_date.isoformat()
                })

        return {"cses": cses, "assets": assets, "analysts": analysts}

    def stream_alerts(self, total_alerts: int, assets: List[Dict[str, Any]]) -> Iterator[Dict[str, Any]]:
        total_seconds = int((self.end_date - self.start_date).total_seconds())

        for _ in range(total_alerts):
            asset = self.rng.choice(assets)
            offset_sec = self.rng.randint(0, total_seconds)
            ts = self.start_date + timedelta(seconds=offset_sec)
            sev = self.rng.choices(self.severities, weights=self.severity_weights, k=1)[0]
            cat = self.rng.choice(self.categories)

            yield {
                "id": str(uuid.uuid4()),
                "cse_id": asset["cse_id"],
                "asset_id": asset["id"],
                "created_at": ts.isoformat(),
                "category": cat,
                "severity": sev,
                "status": "CLOSED" if sev in ("LOW", "MEDIUM") else self.rng.choice(["OPEN", "INVESTIGATING", "CLOSED"]),
                "raw_payload_json": json.dumps({"source": "scale_gen", "event": cat, "severity": sev})
            }
