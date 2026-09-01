"""SAT-SA Phase 13 Controlled Benchmark Dataset & Isolated Ground Truth Builder."""
import json
import os
import uuid
from typing import Dict, List, Tuple, Any
from app.intelligence.models import ScenarioDefinition, GroundTruthEntry
from app.intelligence.manifest_manager import DatasetManifestManager


class Phase13BenchmarkBuilder:
    """Builds the controlled Phase 13 benchmark dataset with 10 realistic scenarios and isolated ground truth."""

    def __init__(self, output_dir: str = "data"):
        self.output_dir = output_dir

    def generate_all_scenarios(self) -> Tuple[List[ScenarioDefinition], List[GroundTruthEntry]]:
        scenarios: List[ScenarioDefinition] = []
        ground_truth: List[GroundTruthEntry] = []

        # 1. Scenario 1: Vulnerable Asset (Log4j CVE-2021-44228)
        scenarios.append(ScenarioDefinition(
            scenario_id="SCENARIO_01_VULNERABLE_ASSET",
            name="Vulnerable Web Server Ingress",
            description="Active web server hosting vulnerable Apache Log4j component with critical CVSS 9.8.",
            category="VULNERABILITY_EXPOSURE",
            source_datasets=["NIST_NVD_2.0", "MITRE_ATTACK_v15"],
            input_entities={"asset_type": "WEB_SERVER", "criticality": "HIGH", "alerts_count": 150},
            expected_condition="Vulnerability detected with high CVSS exposure and mapped ATT&CK T1190 behavior.",
            expected_detection_status="FLAGGED_FOR_TRIAGE",
            expected_threat_context={"cve_id": "CVE-2021-44228", "cvss_score": 9.8, "attack_technique": "T1190"},
            ground_truth_label="HIGH_RISK_VULNERABILITY",
            provenance={"dataset": "NVD_CVE_FEED", "retrieval": "2026-08-31"}
        ))
        ground_truth.append(GroundTruthEntry(
            scenario_id="SCENARIO_01_VULNERABLE_ASSET",
            entity_type="Asset",
            target_id="ASSET_WEB_01",
            is_anomalous=True,
            expected_rules=["NEG-04", "GAP-01"],
            expected_severity="CRITICAL",
            expected_cve="CVE-2021-44228",
            expected_kev=True,
            expected_techniques=["T1190"]
        ))

        # 2. Scenario 2: KEV-Exposed Asset (MOVEit CVE-2023-34362)
        scenarios.append(ScenarioDefinition(
            scenario_id="SCENARIO_02_KEV_EXPOSED_ASSET",
            name="Active CISA KEV Exploited File Transfer",
            description="File transfer server running software actively targeted in ransomware campaigns.",
            category="ACTIVELY_EXPLOITED_KEV",
            source_datasets=["CISA_KEV", "NIST_NVD_2.0"],
            input_entities={"asset_type": "FILE_TRANSFER_SERVER", "criticality": "CRITICAL", "alerts_count": 320},
            expected_condition="CISA KEV membership confirmed with ransomware campaign linkage.",
            expected_detection_status="CONFIRMED_HIGH_PRIORITY",
            expected_threat_context={"cve_id": "CVE-2023-34362", "is_kev": True, "ransomware": "Known"},
            ground_truth_label="CRITICAL_KEV_EXPOSURE",
            provenance={"dataset": "CISA_KEV_CATALOG", "retrieval": "2026-08-31"}
        ))
        ground_truth.append(GroundTruthEntry(
            scenario_id="SCENARIO_02_KEV_EXPOSED_ASSET",
            entity_type="Asset",
            target_id="ASSET_MOVEIT_01",
            is_anomalous=True,
            expected_rules=["NEG-01", "GAP-06"],
            expected_severity="CRITICAL",
            expected_cve="CVE-2023-34362",
            expected_kev=True,
            expected_techniques=["T1190", "T1486"]
        ))

        # 3. Scenario 3: ATT&CK Mapped Activity Chain (T1190 -> T1059 -> T1003)
        scenarios.append(ScenarioDefinition(
            scenario_id="SCENARIO_03_ATTACK_MAPPED_ACTIVITY",
            name="Multi-Stage Attack Chain Activity",
            description="Alert sequence progressing from public exploit to command execution and credential dumping.",
            category="ATTACK_CHAIN_DETECTION",
            source_datasets=["MITRE_ATTACK_v15"],
            input_entities={"alerts_count": 45, "tactics": ["Initial Access", "Execution", "Credential Access"]},
            expected_condition="Correlated ATT&CK technique progression identified in evidence graph.",
            expected_detection_status="CORRELATED_ATTACK_CHAIN",
            expected_threat_context={"techniques": ["T1190", "T1059", "T1003"]},
            ground_truth_label="ATTACK_CHAIN_TRUE_POSITIVE",
            provenance={"dataset": "MITRE_ATTACK_STIX", "retrieval": "2026-08-31"}
        ))
        ground_truth.append(GroundTruthEntry(
            scenario_id="SCENARIO_03_ATTACK_MAPPED_ACTIVITY",
            entity_type="AlertChain",
            target_id="CHAIN_01",
            is_anomalous=True,
            expected_rules=["GAP-01", "GAP-03"],
            expected_severity="HIGH",
            expected_cve=None,
            expected_kev=False,
            expected_techniques=["T1190", "T1059", "T1003"]
        ))

        # 4. Scenario 4: High CVSS Vulnerability Without Known Exploitation
        scenarios.append(ScenarioDefinition(
            scenario_id="SCENARIO_04_VULN_UNEXPLOITED",
            name="Unexploited High-CVSS Component",
            description="Asset with CVSS 8.5 vulnerability that is NOT present in CISA KEV catalog.",
            category="UNEXPLOITED_VULNERABILITY",
            source_datasets=["NIST_NVD_2.0"],
            input_entities={"asset_type": "INTERNAL_DATABASE", "criticality": "MEDIUM"},
            expected_condition="High CVSS noted but zero KEV threat modifier applied.",
            expected_detection_status="STANDARD_PATCHING_QUEUE",
            expected_threat_context={"cvss_score": 8.5, "is_kev": False},
            ground_truth_label="MODERATE_PRIORITY",
            provenance={"dataset": "NVD_CVE_FEED", "retrieval": "2026-08-31"}
        ))
        ground_truth.append(GroundTruthEntry(
            scenario_id="SCENARIO_04_VULN_UNEXPLOITED",
            entity_type="Asset",
            target_id="ASSET_DB_02",
            is_anomalous=False,
            expected_rules=[],
            expected_severity="MEDIUM",
            expected_cve="CVE-2022-3602",
            expected_kev=False,
            expected_techniques=[]
        ))

        # 5. Scenario 5: Actively Exploited Zerologon Domain Controller
        scenarios.append(ScenarioDefinition(
            scenario_id="SCENARIO_05_EXPLOITED_DOMAIN_CONTROLLER",
            name="Domain Controller Privilege Escalation Exposure",
            description="Domain controller running unpatched Netlogon with active CVE-2020-1472 exploitation.",
            category="ACTIVE_EXPLOITATION",
            source_datasets=["CISA_KEV", "MITRE_ATTACK_v15"],
            input_entities={"asset_type": "DOMAIN_CONTROLLER", "criticality": "CRITICAL"},
            expected_condition="Zerologon KEV exposure linked to ATT&CK T1068 and Wizard Spider threat group.",
            expected_detection_status="CRITICAL_SUPERVISORY_ALERT",
            expected_threat_context={"cve_id": "CVE-2020-1472", "is_kev": True, "technique": "T1068"},
            ground_truth_label="CRITICAL_INFRASTRUCTURE_RISK",
            provenance={"dataset": "CISA_KEV_CATALOG", "retrieval": "2026-08-31"}
        ))
        ground_truth.append(GroundTruthEntry(
            scenario_id="SCENARIO_05_EXPLOITED_DOMAIN_CONTROLLER",
            entity_type="Asset",
            target_id="ASSET_DC_01",
            is_anomalous=True,
            expected_rules=["NEG-01", "GAP-05"],
            expected_severity="CRITICAL",
            expected_cve="CVE-2020-1472",
            expected_kev=True,
            expected_techniques=["T1068"]
        ))

        # 6. Scenario 6: Missing Telemetry Silence on High-Risk Asset
        scenarios.append(ScenarioDefinition(
            scenario_id="SCENARIO_06_MISSING_TELEMETRY_SILENCE",
            name="Critical Telemetry Blackout",
            description="Active critical payment gateway experiencing 96h telemetry silence without maintenance log.",
            category="NEGATIVE_SPACE_ANOMALY",
            source_datasets=["SAT-SA_SYNTHETIC"],
            input_entities={"asset_type": "PAYMENT_GATEWAY", "silence_hours": 96, "maintenance": "NONE"},
            expected_condition="NEG-01 Confirmed finding with confidence modifier 1.0.",
            expected_detection_status="CONFIRMED_NEGATIVE_SPACE",
            expected_threat_context={"technique": "T1562.002", "justification": "Event Log Disablement"},
            ground_truth_label="CRITICAL_TELEMETRY_GAP",
            provenance={"dataset": "SAT-SA_GENERATOR", "retrieval": "2026-08-31"}
        ))
        ground_truth.append(GroundTruthEntry(
            scenario_id="SCENARIO_06_MISSING_TELEMETRY_SILENCE",
            entity_type="Asset",
            target_id="ASSET_PAY_01",
            is_anomalous=True,
            expected_rules=["NEG-01"],
            expected_severity="HIGH",
            expected_cve=None,
            expected_kev=False,
            expected_techniques=["T1562.002"]
        ))

        # 7. Scenario 7: Incomplete Investigation & Execution Gap
        scenarios.append(ScenarioDefinition(
            scenario_id="SCENARIO_07_INCOMPLETE_INVESTIGATION",
            name="High Severity Alert Closed Prematurely",
            description="Critical severity ransomware alert closed within 45s without analyst investigation.",
            category="EXECUTION_GAP_ANOMALY",
            source_datasets=["SAT-SA_SYNTHETIC"],
            input_entities={"alert_severity": "CRITICAL", "duration_seconds": 45, "investigation": False},
            expected_condition="GAP-01 and GAP-02 rule evaluations confirmed.",
            expected_detection_status="CONFIRMED_EXECUTION_GAP",
            expected_threat_context={"technique": "T1562.001", "justification": "Rapid Dismissal"},
            ground_truth_label="HIGH_SUPERVISORY_RISK",
            provenance={"dataset": "SAT-SA_GENERATOR", "retrieval": "2026-08-31"}
        ))
        ground_truth.append(GroundTruthEntry(
            scenario_id="SCENARIO_07_INCOMPLETE_INVESTIGATION",
            entity_type="Alert",
            target_id="ALERT_GAP_01",
            is_anomalous=True,
            expected_rules=["GAP-01", "GAP-02"],
            expected_severity="HIGH",
            expected_cve=None,
            expected_kev=False,
            expected_techniques=["T1562.001"]
        ))

        # 8. Scenario 8: Peer-Group Monitoring Anomaly (NEG-04)
        scenarios.append(ScenarioDefinition(
            scenario_id="SCENARIO_08_PEER_GROUP_ANOMALY",
            name="Under-Monitored Peer Asset",
            description="Active critical database generating only 3% of the median event density of its peer group.",
            category="PEER_BASELINE_ANOMALY",
            source_datasets=["SAT-SA_SYNTHETIC"],
            input_entities={"asset_type": "DATABASE", "density_ratio": 0.03, "peer_median": 1200},
            expected_condition="NEG-04 Confirmed finding based on peer density ratio < 0.20.",
            expected_detection_status="CONFIRMED_UNDER_MONITORED",
            expected_threat_context={"technique": "T1190", "justification": "Unmonitored Ingress Point"},
            ground_truth_label="PEER_ANOMALY_TRUE_POSITIVE",
            provenance={"dataset": "SAT-SA_GENERATOR", "retrieval": "2026-08-31"}
        ))
        ground_truth.append(GroundTruthEntry(
            scenario_id="SCENARIO_08_PEER_GROUP_ANOMALY",
            entity_type="Asset",
            target_id="ASSET_PEER_01",
            is_anomalous=True,
            expected_rules=["NEG-04"],
            expected_severity="MEDIUM",
            expected_cve=None,
            expected_kev=False,
            expected_techniques=["T1190"]
        ))

        # 9. Scenario 9: Benign Baseline Activity
        scenarios.append(ScenarioDefinition(
            scenario_id="SCENARIO_09_BENIGN_BASELINE",
            name="Standard Scheduled Operational Baseline",
            description="Routine healthy asset with regular heartbeat telemetry and standard closed investigations.",
            category="BENIGN_ACTIVITY",
            source_datasets=["SAT-SA_SYNTHETIC"],
            input_entities={"asset_type": "WORKSTATION", "status": "ACTIVE", "silence_hours": 2},
            expected_condition="Zero supervisory gap or negative space findings produced.",
            expected_detection_status="BENIGN_CLEAN",
            expected_threat_context={"technique": None, "status": "CLEAN"},
            ground_truth_label="BENIGN_TRUE_NEGATIVE",
            provenance={"dataset": "SAT-SA_GENERATOR", "retrieval": "2026-08-31"}
        ))
        ground_truth.append(GroundTruthEntry(
            scenario_id="SCENARIO_09_BENIGN_BASELINE",
            entity_type="Asset",
            target_id="ASSET_WORKSTATION_01",
            is_anomalous=False,
            expected_rules=[],
            expected_severity="LOW",
            expected_cve=None,
            expected_kev=False,
            expected_techniques=[]
        ))

        # 10. Scenario 10: Mixed-Risk Enterprise Environment
        scenarios.append(ScenarioDefinition(
            scenario_id="SCENARIO_10_MIXED_ENTERPRISE_RISK",
            name="Multi-Tier Enterprise Complex Assessment",
            description="Complex enterprise network containing both hardened assets, KEV exposures, and telemetry gaps.",
            category="MIXED_ENTERPRISE_ASSESSMENT",
            source_datasets=["CISA_KEV", "NIST_NVD_2.0", "MITRE_ATTACK_v15", "SAT-SA_SYNTHETIC"],
            input_entities={"cses_count": 5, "assets_count": 50, "alerts_count": 2500},
            expected_condition="Supervisory risk engine correctly differentiates high-risk CSEs from baseline CSEs.",
            expected_detection_status="MULTI_TIER_RISK_PROFILE",
            expected_threat_context={"high_risk_cses": 2, "moderate_cses": 3},
            ground_truth_label="COMPLEX_BENCHMARK_PORTFOLIO",
            provenance={"dataset": "SAT-SA_BENCHMARK_SUITE", "retrieval": "2026-08-31"}
        ))
        ground_truth.append(GroundTruthEntry(
            scenario_id="SCENARIO_10_MIXED_ENTERPRISE_RISK",
            entity_type="Enterprise",
            target_id="ENTERPRISE_MIXED_01",
            is_anomalous=True,
            expected_rules=["GAP-01", "NEG-01", "NEG-04"],
            expected_severity="HIGH",
            expected_cve="CVE-2023-4966",
            expected_kev=True,
            expected_techniques=["T1190", "T1562.002"]
        ))

        return scenarios, ground_truth

    def build_and_save(self) -> Dict[str, Any]:
        scenarios, ground_truth = self.generate_all_scenarios()
        from app.intelligence.config import get_data_dir
        canonical_data_dir = get_data_dir()

        # Save individual scenarios
        scenario_files = []
        for s in scenarios:
            filename = f"{s.scenario_id.lower()}.json"
            path = os.path.join(canonical_data_dir, "benchmark", "scenarios", filename)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(s.to_dict(), f, indent=2)
            scenario_files.append(filename)

        # Save consolidated benchmark dataset
        benchmark_dataset = {
            "title": "SAT-SA BENCHMARK DATASET — PHASE 13",
            "dataset_name": "SAT-SA BENCHMARK DATASET — PHASE 13",
            "version": "1.0.0",
            "release_date": "2026-09-01",
            "total_scenarios": len(scenarios),
            "scenarios": [s.to_dict() for s in scenarios]
        }
        bm_path = os.path.join(canonical_data_dir, "benchmark", "satsa_phase13_benchmark_dataset.json")
        os.makedirs(os.path.dirname(bm_path), exist_ok=True)
        with open(bm_path, "w", encoding="utf-8") as f:
            json.dump(benchmark_dataset, f, indent=2)

        # Save isolated ground truth
        gt_dataset = {
            "title": "SAT-SA PHASE 13 GROUND TRUTH (STRICTLY ISOLATED)",
            "dataset_name": "SAT-SA PHASE 13 GROUND TRUTH",
            "version": "1.0.0",
            "evaluation_only": True,
            "total_entries": len(ground_truth),
            "entries": [g.to_dict() for g in ground_truth]
        }
        gt_path = os.path.join(canonical_data_dir, "ground_truth", "ground_truth_phase13.json")
        os.makedirs(os.path.dirname(gt_path), exist_ok=True)
        with open(gt_path, "w", encoding="utf-8") as f:
            json.dump(gt_dataset, f, indent=2)

        return {
            "scenarios_count": len(scenarios),
            "ground_truth_count": len(ground_truth),
            "benchmark_dataset_path": os.path.join(canonical_data_dir, "benchmark", "satsa_phase13_benchmark_dataset.json"),
            "ground_truth_path": os.path.join(canonical_data_dir, "ground_truth", "ground_truth_phase13.json")
        }
