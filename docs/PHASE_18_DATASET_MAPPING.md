# SAT-SA — Phase 18 Realistic Cybersecurity Dataset & Threat Intelligence Mapping

## 1. Overview
SAT-SA normalizes multi-source cyber threat intelligence and raw operational telemetry into unified internal schemas. The normalization layer maps heterogeneous schemas deterministically under `STRICT_LOCAL_ONLY` constraints.

---

## 2. Ingested Data Sources & Mappings

### 2.1 CISA Known Exploited Vulnerabilities (KEV) Catalog
- **Source:** CISA KEV Catalog (`data/raw/cisa_kev.json`)
- **Key Fields Mapped:**
  - `cveID` $\to$ `ThreatEntity.cve_id` (e.g. `CVE-2023-34362`)
  - `vendorProject` / `product` $\to$ `ThreatEntity.affected_product`
  - `vulnerabilityName` $\to$ `ThreatEntity.title`
  - `dateAdded` $\to$ `ThreatEntity.date_discovered`
  - `knownRansomwareCampaignUse` $\to$ `ThreatEntity.is_ransomware_associated` (Boolean flag elevating asset criticality)
  - `notes` $\to$ `ThreatEntity.remediation_guidance`

### 2.2 NIST National Vulnerability Database (NVD) CVE Feed
- **Source:** NVD JSON 2.0 (`data/raw/nvd_cve_feed.json`)
- **Key Fields Mapped:**
  - `cve.id` $\to$ `Vulnerability.cve_id`
  - `cve.metrics.cvssMetricV31[0].cvssData.baseScore` $\to$ `Vulnerability.cvss_score`
  - `cve.metrics.cvssMetricV31[0].cvssData.baseSeverity` $\to$ `Vulnerability.severity`
  - `cve.configurations[0].nodes[0].cpeMatch` $\to$ `CPE23` dictionary for automated asset matching

### 2.3 MITRE ATT&CK Enterprise Matrix (STIX 2.1)
- **Source:** MITRE ATT&CK STIX 2.1 (`data/raw/attack_enterprise_stix21.json`)
- **Key Fields Mapped:**
  - `objects[type='attack-pattern'].external_references[source_name='mitre-attack'].external_id` $\to$ `AttackTechnique.technique_id` (e.g. `T1059.001`, `T1078`)
  - `objects[type='attack-pattern'].kill_chain_phases[].phase_name` $\to$ `AttackTechnique.tactic`
  - `objects[type='attack-pattern'].name` $\to$ `AttackTechnique.name`

### 2.4 Operational SIEM / EDR / NIDS Telemetry Alert Stream
- **Source:** Multi-CSE Enterprise Telemetry (`data/benchmark/scenarios/*.json`)
- **Fields Mapped:**
  - `timestamp` $\to$ `Alert.timestamp` (ISO-8601 with UTC normalization)
  - `cse_name` / `sector` $\to$ `CSE` entity mapping
  - `asset_name` / `asset_type` / `cpe` $\to$ `Asset` record
  - `severity` $\to$ `AlertSeverity` enum (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`)
  - `category` $\to$ `AlertCategory` (`FIRMWARE`, `NETWORK`, `PRIVILEGE`, `DEFENSE_EVASION`)
  - `investigation_status` $\to$ `Investigation` closure and duration tracking

---

## 3. Determinism & Data Quality Safeguards
- **Zero Hallucination / Zero Fabrication:** Findings are generated solely from codified supervisory gap rules and codified graph linkages.
- **Deduplication:** Repeated identical alerts on the same asset within a time window are correlated under single root-cause investigation entities.
- **Strict Typing:** All severity, status, and sector strings are validated against Python `Enum` types. Invalid records are routed to `DataQualityIssue` records without interrupting the processing pipeline.
