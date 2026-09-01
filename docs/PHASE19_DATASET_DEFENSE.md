# SAT-SA — PHASE 19 DATASET & THREAT INTELLIGENCE DEFENSE

---

### 1. Dataset Classification Matrix

| Dataset Category | Specific Datasets Ingested | Source & Standard | Operational Purpose |
|---|---|---|---|
| **Authoritative Threat Intelligence** | CISA KEV Catalog, MITRE ATT&CK Enterprise STIX 2.1, NIST NVD CVE Feed | CISA.gov, MITRE.org, NIST.gov | Enrich raw alerts with active exploitation flags, CVSS severity, and adversary tactics. |
| **Realistic Operational Telemetry** | 10 Multi-Sector Enterprise Scenarios (`data/benchmark/scenarios/*.json`) | Power Grid, Banking Core, Telecom Infrastructure | Validates analytical pipeline, gap detection, evidence graph linking, and Chrome UI rendering. |
| **Scalability Stress Benchmark** | 1,000,000 Synthetic Alert Records (`Phase 12 Benchmark`) | Deterministic multi-CSE telemetry generator | Validates chunked batch ingestion, memory stability, and zero-leak database concurrency under high volume. |
| **Future 20-GB Enterprise Archives** | Multi-year raw SIEM log repositories | Enterprise deployment data | Ingestion architecture uses streaming chunked processing (`MAX_INGESTION_CHUNK_SIZE_MB = 50`) to process massive archives without memory exhaustion. |

---

### 2. Defending Common Judge Dataset Questions

#### Q1: "Are you using synthetic data or real-world data?"
> **Answer:** "SAT-SA uses **both**: We ingest authoritative real-world threat intelligence feeds directly from CISA, MITRE, and NIST. For operational telemetry, we validate against structured multi-CSE scenarios representing actual critical infrastructure compromise patterns, while leveraging a 1,000,000-record benchmark to stress-test high-throughput scalability."

#### Q2: "Why didn't you commit the full 20 GB dataset to GitHub?"
> **Answer:** "Committing 20 GB of raw logs to a code repository violates repository hygiene and version control best practices. Instead, SAT-SA is architected with a **streaming, chunked ingestion engine** that processes data in configurable 50 MB batches. This ensures the system runs with a constant memory footprint ($< 85$ MB RAM) regardless of whether the dataset is 100 MB or 20 GB."
