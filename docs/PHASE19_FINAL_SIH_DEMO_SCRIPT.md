# SAT-SA — PHASE 19 FINAL SIH LIVE DEMONSTRATION SCRIPT
## "From Operational Blind Spot to Cryptographically Verifiable Supervisory Finding in 3 Minutes"

**Presenter Target Duration:** 3 to 4 Minutes  
**Demonstration Mode:** 100% Offline Air-Gapped (`http://127.0.0.1:8000/`)  

---

### ACT 1: Sovereign Air-Gapped Launch (0:00 – 0:30)
1. **Action:** Open terminal and run `.\scripts\start_offline_satsa.bat`. Run `python scripts/health_check.py 8000`.
2. **Spoken Pitch:**
   > *"Good morning, esteemed judges. We are demonstrating SAT-SA, a sovereign, 100% air-gapped supervisory analytics platform built for national cybersecurity regulators like NCIIPC and CERT-In. Notice our health probe confirms 24 active relational tables and strict air-gap compliance with zero external cloud dependencies."*
3. **Screen:** Amber **STRICT LOCAL / AIR-GAP** banner rendered in Chrome.

---

### ACT 2: National Multi-Sector Posture (0:30 – 1:15)
1. **Action:** Navigate to Supervisory Dashboard (`/`).
2. **Spoken Pitch:**
   > *"Existing SIEMs operate within a single enterprise boundary. SAT-SA operates at the supervisory tier above hundreds of critical entities across Power, Banking, and Telecom. Our dashboard immediately decomposes national supervisory risk into 5 explainable components: Execution Gaps, Negative Space silences, Peer Deviations, Alert Anomalies, and Asset Criticalities."*
3. **Screen:** Multi-CSE risk cards with color-coded risk bands.

---

### ACT 3: Uncovering the SOC Execution Gap (1:15 – 2:00)
1. **Action:** Click **REVIEW PRIORITY QUEUE**.
2. **Spoken Pitch:**
   > *"Here is the core breakthrough: An entity's internal SOC might mark a critical alert as closed, but our Execution Gap Engine detects that a critical SCADA RTU firmware alert under active CISA KEV exploitation was closed with zero forensic triage (GAP-01). Furthermore, our Negative Space Matrix caught a 12-hour telemetry drop on a primary substation gateway (GAP-02). Notice our 2-pass prioritization algorithm balances highest risk with sectoral diversity so no single entity monopolizes examiner attention."*
3. **Screen:** Prioritized queue table with rank, score decomposition, and tags.

---

### ACT 4: Bipartite Evidence Graph Drill-Down (2:00 – 2:45)
1. **Action:** Click **SUPERVISORY EVIDENCE GRAPH**.
2. **Spoken Pitch:**
   > *"Unlike black-box AI tools, every finding in SAT-SA is grounded in topological evidence. In one click, an examiner traces this critical finding directly to the physical asset, the raw SIEM alert payload, and the active MITRE ATT&CK lateral movement technique."*
3. **Screen:** Interactive NetworkX graph canvas linking alerts, assets, and findings.

---

### ACT 5: Cryptographic Snapshot & Audit Chain Proof (2:45 – 3:30)
1. **Action:** Navigate to **REPORTS & AUDIT TRAIL**. Open Executive Snapshot drawer. Switch to Audit tab and click **Verify Audit Integrity**.
2. **Spoken Pitch:**
   > *"Regulatory sanctions require legal defensibility. Every report snapshot is sealed with a canonical SHA-256 hash. If anyone tampers with a single byte in the database, the UI immediately flags it with a rose 'Tampered' warning. Our append-only cryptographic audit chain verifies all 65 events in milliseconds. SAT-SA does not merely monitor alerts — it audits the integrity of national cyber defence."*
3. **Screen:** Green `Verified` SHA-256 badge and `ALL AUDIT TRAIL RECORDS CRYPTOGRAPHICALLY VERIFIED` banner.
