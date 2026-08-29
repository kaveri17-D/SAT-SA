import random
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Tuple, Any
import numpy as np

from app.ingestion.generator.config import GeneratorConfig
from app.ingestion.generator.ground_truth import (
    GroundTruthScenario, DatasetManifest, ScenarioClass, ScenarioType
)
from app.models import (
    CSE, Asset, Analyst, Alert, Investigation, Escalation, Case, Closure,
    AssetCriticality, AlertSeverity, DispositionType
)


class SyntheticDatasetGenerator:
    """Deterministic, ground-truth-labeled synthetic dataset generator for SAT-SA."""

    def __init__(self, config: GeneratorConfig = None):
        self.config = config or GeneratorConfig.baseline_preset()
        self.rng = random.Random(self.config.seed)
        self.np_rng = np.random.default_rng(self.config.seed)
        
        # Generated entity collections
        self.cses: List[CSE] = []
        self.assets: List[Asset] = []
        self.analysts: List[Analyst] = []
        self.alerts: List[Alert] = []
        self.investigations: List[Investigation] = []
        self.escalations: List[Escalation] = []
        self.cases: List[Case] = []
        self.closures: List[Closure] = []
        self.maintenance_logs: List[Dict[str, Any]] = []
        
        # Ground truth manifests (strictly isolated from domain records)
        self.ground_truth_scenarios: List[GroundTruthScenario] = []

    def _next_uuid(self) -> uuid.UUID:
        """Generate deterministic UUID seeded by generator instance state."""
        return uuid.UUID(int=self.rng.getrandbits(128), version=4)

    def generate(self) -> Dict[str, Any]:
        """Execute full deterministic generation pipeline."""
        self._generate_cses()
        self._generate_assets()
        self._generate_analysts()
        self._generate_baseline_workflows()
        self._inject_scenarios()

        manifest = DatasetManifest(
            generator_version="1.0.0",
            seed=self.config.seed,
            generated_at=datetime.now(timezone.utc).isoformat(),
            record_counts={
                "cses": len(self.cses),
                "assets": len(self.assets),
                "analysts": len(self.analysts),
                "alerts": len(self.alerts),
                "investigations": len(self.investigations),
                "escalations": len(self.escalations),
                "cases": len(self.cases),
                "closures": len(self.closures),
                "maintenance_logs": len(self.maintenance_logs)
            },
            scenario_counts=self._count_scenarios_by_class(),
            time_range={
                "start": self.config.start_date.isoformat(),
                "end": (self.config.start_date + timedelta(days=self.config.duration_days)).isoformat()
            },
            ground_truth_scenarios=self.ground_truth_scenarios
        )

        return {
            "cses": self.cses,
            "assets": self.assets,
            "analysts": self.analysts,
            "alerts": self.alerts,
            "investigations": self.investigations,
            "escalations": self.escalations,
            "cases": self.cases,
            "closures": self.closures,
            "maintenance_logs": self.maintenance_logs,
            "manifest": manifest
        }

    def _generate_cses(self):
        """Generate CSE entities across sectors, including CSE-07 narrative target."""
        for i in range(1, self.config.num_cses + 1):
            if i == 7 or (self.config.num_cses < 7 and i == 1):
                # CSE-07: Controlled narrative anomaly target
                name = "CSE-07 Strategic Power Grid Corp"
                sector = "ENERGY"
                entity_type = "CRITICAL_GRID_OPERATOR"
                size_tier = "TIER_1"
            else:
                sector = self.config.sectors[(i - 1) % len(self.config.sectors)]
                entity_type = f"{sector}_OPERATOR"
                size_tier = self.config.size_tiers[(i - 1) % len(self.config.size_tiers)]
                name = f"CSE-{i:02d} Critical {sector.capitalize()} Entity"

            cse = CSE(
                id=self._next_uuid(),
                name=name,
                sector=sector,
                entity_type=entity_type,
                size_tier=size_tier,
                metadata_json={
                    "region": f"REGION_{((i - 1) % 4) + 1}",
                    "compliance_baseline": "NCIIPC_V2"
                }
            )
            self.cses.append(cse)

    def _generate_assets(self):
        """Generate assets per CSE with realistic criticality distribution."""
        asset_types = ["SCADA_CONTROLLER", "DOMAIN_CONTROLLER", "DATABASE_SERVER", "FIREWALL_GATEWAY", "WORKSTATION"]
        criticalities = [AssetCriticality.CRITICAL, AssetCriticality.HIGH, AssetCriticality.MEDIUM, AssetCriticality.LOW]
        crit_weights = [0.15, 0.35, 0.35, 0.15]

        for cse in self.cses:
            num_assets = self.rng.randint(self.config.assets_per_cse_min, self.config.assets_per_cse_max)
            for j in range(1, num_assets + 1):
                asset_type = self.rng.choice(asset_types)
                crit = self.rng.choices(criticalities, weights=crit_weights)[0]
                
                asset = Asset(
                    id=self._next_uuid(),
                    cse_id=cse.id,
                    name=f"{cse.name[:6]}-{asset_type}-{j:02d}",
                    asset_type=asset_type,
                    criticality=crit,
                    status="ACTIVE",
                    decommissioned_at=None
                )
                self.assets.append(asset)

    def _generate_analysts(self):
        """Generate SOC analysts per CSE."""
        roles = ["ANALYST_L1", "ANALYST_L2", "SOC_LEAD"]
        for cse in self.cses:
            num_analysts = self.rng.randint(3, 8)
            for k in range(1, num_analysts + 1):
                role = roles[0] if k <= num_analysts - 2 else (roles[1] if k == num_analysts - 1 else roles[2])
                analyst = Analyst(
                    id=self._next_uuid(),
                    cse_id=cse.id,
                    handle=f"{cse.name[:6].lower()}_analyst_{k:02d}",
                    role=role
                )
                self.analysts.append(analyst)

    def _generate_baseline_workflows(self):
        """Generate normal, plausible operational workflows over the time window."""
        categories = ["AUTHENTICATION_FAILURE", "MALWARE_DETECTION", "UNAUTHORIZED_PORT_SCAN", "PRIVILEGE_ESCALATION"]
        severities = [AlertSeverity.CRITICAL, AlertSeverity.HIGH, AlertSeverity.MEDIUM, AlertSeverity.LOW, AlertSeverity.INFO]
        sev_weights = [0.10, 0.25, 0.40, 0.20, 0.05]

        cse_assets: Dict[uuid.UUID, List[Asset]] = {}
        for asset in self.assets:
            cse_assets.setdefault(asset.cse_id, []).append(asset)

        cse_analysts: Dict[uuid.UUID, List[Analyst]] = {}
        for analyst in self.analysts:
            cse_analysts.setdefault(analyst.cse_id, []).append(analyst)

        alerts_per_cse = self.config.total_alerts // len(self.cses)

        for cse in self.cses:
            assets = cse_assets.get(cse.id, [])
            analysts = cse_analysts.get(cse.id, [])
            if not assets or not analysts:
                continue

            for _ in range(alerts_per_cse):
                asset = self.rng.choice(assets)
                analyst = self.rng.choice(analysts)
                
                offset_seconds = self.rng.randint(0, self.config.duration_days * 86400)
                alert_time = self.config.start_date + timedelta(seconds=offset_seconds)
                
                sev = self.rng.choices(severities, weights=sev_weights)[0]
                category = self.rng.choice(categories)

                alert = Alert(
                    id=self._next_uuid(),
                    cse_id=cse.id,
                    asset_id=asset.id,
                    source_system=f"SIEM_SENSOR_{self.rng.randint(1, 5)}",
                    category=category,
                    severity=sev,
                    raw_severity=sev.value,
                    status="CLOSED",
                    created_at=alert_time,
                    updated_at=alert_time + timedelta(minutes=self.rng.randint(30, 300))
                )
                self.alerts.append(alert)

                if self.rng.random() < 0.85:
                    inv_start = alert_time + timedelta(minutes=self.rng.randint(1, 15))
                    inv_dur = self.rng.randint(300, 3600)
                    inv_end = inv_start + timedelta(seconds=inv_dur)
                    
                    inv = Investigation(
                        id=self._next_uuid(),
                        alert_id=alert.id,
                        analyst_id=analyst.id,
                        started_at=inv_start,
                        ended_at=inv_end,
                        duration_seconds=inv_dur,
                        notes=f"Standard investigation of {category} on {asset.name}. Verified logs.",
                        outcome="RESOLVED",
                        created_at=inv_start,
                        updated_at=inv_end
                    )
                    self.investigations.append(inv)

                    if sev in (AlertSeverity.CRITICAL, AlertSeverity.HIGH) and self.rng.random() < 0.60:
                        esc_time = inv_start + timedelta(minutes=self.rng.randint(5, 20))
                        esc = Escalation(
                            id=self._next_uuid(),
                            investigation_id=inv.id,
                            escalated_to="SOC_LEAD_TIER2",
                            escalated_at=esc_time,
                            reason=f"High severity {sev.value} alert requiring tier-2 validation.",
                            created_at=esc_time,
                            updated_at=esc_time
                        )
                        self.escalations.append(esc)

                        case_open = esc_time + timedelta(minutes=5)
                        case_close = case_open + timedelta(hours=self.rng.randint(2, 48))
                        case = Case(
                            id=self._next_uuid(),
                            cse_id=cse.id,
                            status="CLOSED",
                            opened_at=case_open,
                            closed_at=case_close,
                            created_at=case_open,
                            updated_at=case_close
                        )
                        self.cases.append(case)

                        closure = Closure(
                            id=self._next_uuid(),
                            case_id=case.id,
                            disposition_type=DispositionType.TRUE_POSITIVE if self.rng.random() < 0.7 else DispositionType.BENIGN_POSITIVE,
                            closed_by=analyst.handle,
                            closed_at=case_close,
                            justification="Verified containment and mitigation applied successfully.",
                            created_at=case_close,
                            updated_at=case_close
                        )
                        self.closures.append(closure)

    def _inject_scenarios(self):
        """Inject explicit ground-truth labeled anomaly & exception scenarios."""
        self._inject_execution_gaps()
        self._inject_negative_space()
        self._inject_cse07_peer_anomaly()
        self._inject_legitimate_exceptions()

    def _inject_execution_gaps(self):
        """Inject execution gap anomalies."""
        cse = self.cses[1 % len(self.cses)]
        asset_candidates = [a for a in self.assets if a.cse_id == cse.id and a.criticality == AssetCriticality.CRITICAL]
        asset = asset_candidates[0] if asset_candidates else self.assets[0]
        alert_time = self.config.start_date + timedelta(days=10)
        
        gap1_alert = Alert(
            id=self._next_uuid(),
            cse_id=cse.id,
            asset_id=asset.id,
            source_system="CRITICAL_GRID_SENSOR",
            category="EXFILTRATION_SUSPICION",
            severity=AlertSeverity.CRITICAL,
            raw_severity="CRITICAL",
            status="CLOSED",
            created_at=alert_time,
            updated_at=alert_time + timedelta(minutes=10)
        )
        self.alerts.append(gap1_alert)

        gap1_inv = Investigation(
            id=self._next_uuid(),
            alert_id=gap1_alert.id,
            analyst_id=self.analysts[0].id,
            started_at=alert_time + timedelta(minutes=2),
            ended_at=alert_time + timedelta(minutes=8),
            duration_seconds=360,
            notes="Closed critical alert quickly without escalation.",
            outcome="CLOSED",
            created_at=alert_time + timedelta(minutes=2),
            updated_at=alert_time + timedelta(minutes=8)
        )
        self.investigations.append(gap1_inv)

        self.ground_truth_scenarios.append(GroundTruthScenario(
            scenario_id=f"SCEN-GAP-01-{self._next_uuid().hex[:6]}",
            scenario_class=ScenarioClass.EXECUTION_GAP,
            scenario_type=ScenarioType.CRITICAL_ALERT_NO_ESCALATION,
            target_entity_id=str(gap1_alert.id),
            target_entity_type="Alert",
            expected_finding_rule="GAP-01",
            is_legitimate_exception=False,
            description="Critical severity alert investigated and closed with NO escalation record."
        ))

        gap3_alert = Alert(
            id=self._next_uuid(),
            cse_id=cse.id,
            asset_id=asset.id,
            source_system="SIEM_CORE",
            category="MALWARE_DETECTION",
            severity=AlertSeverity.HIGH,
            raw_severity="HIGH",
            status="CLOSED",
            created_at=alert_time + timedelta(days=2),
            updated_at=alert_time + timedelta(days=2, minutes=1)
        )
        self.alerts.append(gap3_alert)

        gap3_inv = Investigation(
            id=self._next_uuid(),
            alert_id=gap3_alert.id,
            analyst_id=self.analysts[0].id,
            started_at=alert_time + timedelta(days=2, seconds=10),
            ended_at=alert_time + timedelta(days=2, seconds=18),
            duration_seconds=8,
            notes="ok",
            outcome="RESOLVED",
            created_at=alert_time + timedelta(days=2, seconds=10),
            updated_at=alert_time + timedelta(days=2, seconds=18)
        )
        self.investigations.append(gap3_inv)

        self.ground_truth_scenarios.append(GroundTruthScenario(
            scenario_id=f"SCEN-GAP-03-{self._next_uuid().hex[:6]}",
            scenario_class=ScenarioClass.EXECUTION_GAP,
            scenario_type=ScenarioType.HASTY_INVESTIGATION_DURATION,
            target_entity_id=str(gap3_inv.id),
            target_entity_type="Investigation",
            expected_finding_rule="GAP-03",
            is_legitimate_exception=False,
            description="Investigation duration was 8 seconds (far below 450s peer median)."
        ))

    def _inject_negative_space(self):
        """Inject missing expected evidence (Negative Space) scenarios for NEG-01 through NEG-05."""
        cse = self.cses[2 % len(self.cses)]
        
        # NEG-01: Critical Asset Missing Telemetry
        neg1_asset = Asset(
            id=self._next_uuid(),
            cse_id=cse.id,
            name=f"{cse.name[:6]}-SCADA-SILENT-CRITICAL",
            asset_type="SCADA_CONTROLLER",
            criticality=AssetCriticality.CRITICAL,
            status="ACTIVE",
            decommissioned_at=None
        )
        self.assets.append(neg1_asset)

        self.ground_truth_scenarios.append(GroundTruthScenario(
            scenario_id=f"SCEN-NEG-01-{self._next_uuid().hex[:6]}",
            scenario_class=ScenarioClass.NEGATIVE_SPACE,
            scenario_type=ScenarioType.CRITICAL_ASSET_MISSING_TELEMETRY,
            target_entity_id=str(neg1_asset.id),
            target_entity_type="Asset",
            expected_finding_rule="NEG-01",
            is_legitimate_exception=False,
            description="Active CRITICAL SCADA asset has zero telemetry or alert records across window."
        ))

        # NEG-02: Sudden Telemetry Drop across CSE
        neg2_cse = CSE(
            id=self._next_uuid(),
            name="CSE-99 Telemetry Drop Blackout Entity",
            sector="TELECOM",
            entity_type="TELECOM_OPERATOR",
            size_tier="TIER_2",
            metadata_json={"region": "REGION_4"}
        )
        self.cses.append(neg2_cse)

        self.ground_truth_scenarios.append(GroundTruthScenario(
            scenario_id=f"SCEN-NEG-02-{self._next_uuid().hex[:6]}",
            scenario_class=ScenarioClass.NEGATIVE_SPACE,
            scenario_type=ScenarioType.SUDDEN_TELEMETRY_DROP,
            target_entity_id=str(neg2_cse.id),
            target_entity_type="CSE",
            expected_finding_rule="NEG-02",
            is_legitimate_exception=False,
            description="CSE-99 exhibits sudden 100% telemetry blackout with zero alerts ingested."
        ))

        # NEG-03: Missing Expected High-Risk Category for CSE
        self.ground_truth_scenarios.append(GroundTruthScenario(
            scenario_id=f"SCEN-NEG-03-{self._next_uuid().hex[:6]}",
            scenario_class=ScenarioClass.NEGATIVE_SPACE,
            scenario_type=ScenarioType.MISSING_ALERT_CATEGORY,
            target_entity_id=str(cse.id),
            target_entity_type="CSE",
            expected_finding_rule="NEG-03",
            is_legitimate_exception=False,
            description="CSE has active alert feed but zero MALWARE_DETECTION alerts in portfolio."
        ))

        # NEG-04: Critical Asset Under-Monitoring vs Peer Group
        neg4_asset = Asset(
            id=self._next_uuid(),
            cse_id=cse.id,
            name=f"{cse.name[:6]}-UNDER-MONITORED-SCADA",
            asset_type="SCADA_CONTROLLER",
            criticality=AssetCriticality.CRITICAL,
            status="ACTIVE",
            decommissioned_at=None
        )
        self.assets.append(neg4_asset)

        self.ground_truth_scenarios.append(GroundTruthScenario(
            scenario_id=f"SCEN-NEG-04-{self._next_uuid().hex[:6]}",
            scenario_class=ScenarioClass.NEGATIVE_SPACE,
            scenario_type=ScenarioType.UNDER_MONITORED_CRITICAL_ASSET,
            target_entity_id=str(neg4_asset.id),
            target_entity_type="Asset",
            expected_finding_rule="NEG-04",
            is_legitimate_exception=False,
            description="Critical SCADA node exhibits < 20% of peer group telemetry density."
        ))

        # NEG-05: Unexplained Maintenance Silence
        neg5_asset = Asset(
            id=self._next_uuid(),
            cse_id=cse.id,
            name=f"{cse.name[:6]}-UNEXPLAINED-SILENCE-NODE",
            asset_type="SCADA_CONTROLLER",
            criticality=AssetCriticality.CRITICAL,
            status="ACTIVE",
            decommissioned_at=None
        )
        self.assets.append(neg5_asset)

        self.ground_truth_scenarios.append(GroundTruthScenario(
            scenario_id=f"SCEN-NEG-05-{self._next_uuid().hex[:6]}",
            scenario_class=ScenarioClass.NEGATIVE_SPACE,
            scenario_type=ScenarioType.UNEXPLAINED_MAINTENANCE_SILENCE,
            target_entity_id=str(neg5_asset.id),
            target_entity_type="Asset",
            expected_finding_rule="NEG-05",
            is_legitimate_exception=False,
            description="Critical node has complete operational silence with NO matching maintenance log record."
        ))

    def _inject_cse07_peer_anomaly(self):
        """Inject CSE-07 narrative anomaly: High alert volume but suspicious low escalation rate."""
        cse07_candidates = [c for c in self.cses if "CSE-07" in c.name or "Strategic Power" in c.name]
        if cse07_candidates:
            cse07 = cse07_candidates[0]
        else:
            cse07 = self.cses[0]
        cse07_asset = [a for a in self.assets if a.cse_id == cse07.id][0]
        cse07_analyst = [an for an in self.analysts if an.cse_id == cse07.id][0]

        for m in range(150):
            alert_time = self.config.start_date + timedelta(hours=m * 8)
            alt = Alert(
                id=self._next_uuid(),
                cse_id=cse07.id,
                asset_id=cse07_asset.id,
                source_system="CSE07_SCADA_SENSOR",
                category="PRIVILEGE_ESCALATION",
                severity=AlertSeverity.CRITICAL,
                raw_severity="CRITICAL",
                status="CLOSED",
                created_at=alert_time,
                updated_at=alert_time + timedelta(seconds=15)
            )
            self.alerts.append(alt)

            inv = Investigation(
                id=self._next_uuid(),
                alert_id=alt.id,
                analyst_id=cse07_analyst.id,
                started_at=alert_time + timedelta(seconds=2),
                ended_at=alert_time + timedelta(seconds=10),
                duration_seconds=8,
                notes="Templated auto-close notes: verified benign.",
                outcome="RESOLVED",
                created_at=alert_time + timedelta(seconds=2),
                updated_at=alert_time + timedelta(seconds=10)
            )
            self.investigations.append(inv)

        self.ground_truth_scenarios.append(GroundTruthScenario(
            scenario_id=f"SCEN-PEER-CSE07-{self._next_uuid().hex[:6]}",
            scenario_class=ScenarioClass.PEER_ANOMALY,
            scenario_type=ScenarioType.CSE07_SUPERVISORY_DEVIATION,
            target_entity_id=str(cse07.id),
            target_entity_type="CSE",
            expected_finding_rule="PEER-01",
            is_legitimate_exception=False,
            description="CSE-07 has 150+ critical SCADA alerts with 0% escalation rate vs peer median 18.5%."
        ))

    def _inject_legitimate_exceptions(self):
        """Inject legitimate operational exceptions to test false positive suppression."""
        cse = self.cses[min(3, len(self.cses) - 1)]
        
        maint_asset = Asset(
            id=self._next_uuid(),
            cse_id=cse.id,
            name=f"{cse.name[:6]}-MAINT-SCADA",
            asset_type="SCADA_CONTROLLER",
            criticality=AssetCriticality.CRITICAL,
            status="ACTIVE",
            decommissioned_at=None
        )
        self.assets.append(maint_asset)

        maint_start = self.config.start_date + timedelta(days=15)
        maint_end = maint_start + timedelta(days=20)
        
        self.maintenance_logs.append({
            "id": str(self._next_uuid()),
            "asset_id": str(maint_asset.id),
            "cse_id": str(cse.id),
            "maintenance_ref": "MAINT_LOG_2026_015",
            "start_time": maint_start.isoformat(),
            "end_time": maint_end.isoformat(),
            "reason": "Scheduled firmware overhaul on SCADA node.",
            "approved_by": "CHIEF_ENGINEER"
        })

        self.ground_truth_scenarios.append(GroundTruthScenario(
            scenario_id=f"SCEN-EXCEPT-MAINT-{self._next_uuid().hex[:6]}",
            scenario_class=ScenarioClass.LEGITIMATE_EXCEPTION,
            scenario_type=ScenarioType.MAINTENANCE_WINDOW_EXPLANATION,
            target_entity_id=str(maint_asset.id),
            target_entity_type="Asset",
            expected_finding_rule="NEG-01",
            is_legitimate_exception=True,
            exception_reason="LOGGED_MAINTENANCE_WINDOW",
            description="Missing telemetry on critical asset is explained by active maintenance record MAINT_LOG_2026_015."
        ))

        decom_time = self.config.start_date + timedelta(days=5)
        decom_asset = Asset(
            id=self._next_uuid(),
            cse_id=cse.id,
            name=f"{cse.name[:6]}-DECOM-SERVER",
            asset_type="DATABASE_SERVER",
            criticality=AssetCriticality.HIGH,
            status="DECOMMISSIONED",
            decommissioned_at=decom_time
        )
        self.assets.append(decom_asset)

        self.ground_truth_scenarios.append(GroundTruthScenario(
            scenario_id=f"SCEN-EXCEPT-DECOM-{self._next_uuid().hex[:6]}",
            scenario_class=ScenarioClass.LEGITIMATE_EXCEPTION,
            scenario_type=ScenarioType.DECOMMISSIONED_ASSET_EXPLANATION,
            target_entity_id=str(decom_asset.id),
            target_entity_type="Asset",
            expected_finding_rule="NEG-01",
            is_legitimate_exception=True,
            exception_reason="DECOMMISSIONED_STATUS",
            description="Missing alerts on high-criticality database server explained by DECOMMISSIONED status."
        ))

    def _count_scenarios_by_class(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for s in self.ground_truth_scenarios:
            key = s.scenario_class.value
            counts[key] = counts.get(key, 0) + 1
        return counts
