# SAT-SA — PHASE 19 TECHNICAL ARCHITECTURE MANUAL

---

### 1. End-to-End Supervisory Pipeline Architecture

```
+---------------------------------------------------------------------------------------------------+
|                               1. MULTI-SOURCE INGESTION & NORMALIZATION                           |
|  - Telemetry: SIEM (Splunk), NIDS (Suricata), EDR (CrowdStrike)                                    |
|  - Threat Intel: CISA KEV, MITRE ATT&CK STIX 2.1, NIST NVD CVE Feed                                |
|  - Normalization: Schema mapping, UTC ISO-8601 formatting, CPE23 asset dictionary matching         |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|                                   2. SUPERVISORY ANALYTICAL CORE                                  |
|  +-------------------------------------+  +----------------------------------------------------+  |
|  |     EXECUTION GAP ENGINE            |  |             NEGATIVE SPACE MATRIX                  |  |
|  |  - GAP-01: Critical Alert Untriaged |  |  - NEG-01: Agent Telemetry Silence                 |  |
|  |  - GAP-02: Missing Investigation    |  |  - NEG-02: Sensor Coverage Drops                   |  |
|  |  - GAP-03: Hasty Triage Below Peer  |  |  - NEG-03: Unmonitored Asset Blind Spots           |  |
|  |  - GAP-04..06: False Positive Abuse |  |  - NEG-04: Logging Pipeline Tampering              |  |
|  +-------------------------------------+  +----------------------------------------------------+  |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|                               3. RISK DECOMPOSITION & PRIORITIZATION                              |
|  - 5-Component Mathematical Risk: 30% Gap + 25% NegSpace + 20% Peer + 15% Anomaly + 10% Criticality|
|  - 2-Pass Diversity Prioritization: Pass 1 (Sector/Category Quotas) + Pass 2 (Residual Risk Max) |
|  - Topological Evidence Graph: NetworkX bipartite graph linking Alerts <-> Assets <-> Findings     |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|                               4. REST API & EXAMINER CONSOLE INTERFACE                            |
|  - Backend Gateway: FastAPI with Pydantic type validation & 27 registered endpoints               |
|  - Single-Origin SPA: React 18, TypeScript, Tailwind CSS, Lucide icons, Vite bundle              |
|  - Diagnostic Probes: /api/v1/health/live (Liveness) & /api/v1/health/ready (Deep Diagnostics)     |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
+---------------------------------------------------------------------------------------------------+
|                          5. CRYPTOGRAPHIC IMMUTABILITY & AUDIT TRAIL LAYER                         |
|  - Snapshot Sealing: Canonical SHA-256 report snapshot payload hashing                            |
|  - Chained Audit Ledger: Genesis-anchored append-only backward hash pointer chain                |
|  - Tamper Defense: Real-time UI warning badge on database modifications                           |
|  - Disaster Recovery: Point-in-time SQLite online backups with .sha256 sidecar verification       |
+---------------------------------------------------------------------------------------------------+
```

---

### 2. Architectural Invariants
1. **Mathematical Determinism:** All gap evaluations, risk scores, and queue ranks are 100% reproducible across repeated runs.
2. **Air-Gap Invariant:** Enforced via `STRICT_LOCAL_ONLY = True` (0 external network requests).
3. **Decoupled Architecture:** Single unified FastAPI server serves both REST APIs and compiled static SPA bundle over local loopback (`http://127.0.0.1:8000/`).
