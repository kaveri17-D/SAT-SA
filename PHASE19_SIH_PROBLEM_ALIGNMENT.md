# SAT-SA — PHASE 19 SIH PROBLEM STATEMENT 26157 ALIGNMENT

**Problem Statement:** SIH 26157 — Supervisory Analytics Tool for Security Analytics (SAT-SA)  
**Target Beneficiaries:** National Cyber Authorities (NCIIPC, CERT-In), Sectoral Regulators (RBI, CEA, TRAI), Supervisory Security Examiners, and Chief Information Security Officers (CISOs) of Critical Sector Entities (CSEs).  

---

### SIH Requirement-to-Capability Alignment Matrix

| SIH Requirement | SAT-SA Implemented Capability | Underlying Technical Mechanism | Verification Evidence |
|---|---|---|---|
| **1. Multi-Entity Supervisory Telemetry Aggregation** | Ingests alerts from heterogeneous SIEM, NIDS, and EDR systems across critical sectors (Energy, Banking, Telecom). | Ingestion Pipeline with schema normalizer and CPE asset matcher. | `test_end_to_end_pipeline.py` & Multi-CSE benchmark scenarios |
| **2. SOC Operational Execution Gap Detection** | Detects when SOCs fail to investigate critical alerts, close tickets prematurely, or mark true attacks as false positives. | Execution Gap Engine (`GAP-01` to `GAP-06`) codified as deterministic rules. | `test_adversarial_and_edge_cases.py` (Finding generated on hasty closure) |
| **3. Negative Space & Silent Asset Detection** | Identifies assets experiencing abnormal monitoring silence, agent tampering, or log drop anomalies. | Negative Space Matrix (`NEG-01` to `NEG-04`) tracking expected baseline heartbeats. | `test_adversarial_and_edge_cases.py` (`GAP-02` telemetry drop finding) |
| **4. Threat Intelligence Cross-Referencing** | Enriches alerts with CISA KEV (exploited CVEs) and MITRE ATT&CK enterprise tactics/techniques. | Threat Normalizer & Intelligence Parsers (`data/raw/`). | `test_threat_mapper_and_enrichment.py` |
| **5. Explainable 5-Component Risk Scoring** | Replaces opaque black-box scores with mathematical risk breakdown: Gap (30%), Negative Space (25%), Peer Deviation (20%), Anomaly (15%), Asset Criticality (10%). | `SupervisoryRiskEngine` (`app/analytics/risk_engine.py`). | `test_risk_engine.py` (Evaluates 22 CSEs in 0.33s) |
| **6. Diversity-Aware Review Prioritization** | Generates an optimal review queue balancing highest risk severity with sectoral diversity to prevent single-entity flooding. | 2-Pass Prioritization Algorithm (`app/analytics/prioritization_engine.py`). | `test_prioritization_engine.py` (Pass-1 diversity, Pass-2 priority) |
| **7. Bipartite Evidence Graph Analysis** | Visually and topologically links Alerts $\to$ Assets $\to$ Findings $\to$ Threat Entities. | `SupervisoryEvidenceGraphEngine` (NetworkX graph canvas in UI). | `test_evidence_graph_and_queries.py` & Chrome UI screenshot `03_graph.png` |
| **8. Legal Non-Repudiation & Auditability** | Immutably signs assessment report snapshots with SHA-256 and maintains an append-only cryptographic audit hash chain. | `SnapshotManager` & `AuditService` (`app/audit/`). | `test_audit_service_and_chaining.py` & Chrome UI screenshot `05_report_details.png` |
| **9. 100% Air-Gapped / Offline Deployment** | Runs with zero external internet dependencies, zero cloud API tokens, and bundled local assets. | `STRICT_LOCAL_ONLY = True` configuration with unified single-port FastAPI serving. | `PHASE19_AIRGAP_FINAL_CERTIFICATION.md` (0 external socket calls) |
| **10. Tamper Detection & Integrity Verification** | Detects direct unauthorized SQL database edits and flags affected reports with visual warning badges. | Real-time hash recalculation in `SnapshotManager`. | Playwright Chrome screenshot `07_tamper_detected.png` |
