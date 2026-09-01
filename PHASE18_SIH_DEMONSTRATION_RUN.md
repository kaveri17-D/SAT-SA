# SAT-SA — PHASE 18 SIH DEMONSTRATION WORKFLOW RUNBOOK
## Repeatable, Evidence-Based National Cyber-Supervisory Audit Demonstration

**Demonstration Platform:** SAT-SA (Smart Assessment Tool for Security Analytics)  
**Target Environment:** Air-Gapped / Isolated Demonstration Laptop or Server  
**Audience:** SIH Grand Finale Evaluators / National Cybersecurity Authorities (NCIIPC / CERT-In)  
**Air-Gap Guarantee:** `STRICT_LOCAL_ONLY = True` (0 Outbound Internet Calls)  

---

### Phase 18 Live Demonstration Sequence

| Step | Action / Workflow | Command / UI Interaction | Expected Observation & Evaluator Proof |
|:---:|---|---|---|
| **1** | **Cold-Start Launch** | `.\scripts\start_offline_satsa.bat` | Unified server starts on `http://127.0.0.1:8000/`. Zero cloud/CDN dependencies. |
| **2** | **Health & Readiness Probe** | `python scripts/health_check.py 8000` | HTTP 200 `status: ready`, 24 DB tables active, disk space healthy, `airgap_mode: true`. |
| **3** | **Open Examiner Console** | Navigate to `http://127.0.0.1:8000/` in Chrome | Amber **STRICT LOCAL / AIR-GAP** banner rendered. System shows high-level posture across CSEs. |
| **4** | **Supervisory Dashboard** | Review CSE Risk Cards & Metrics | Inspect Energy (`NORTHERN_REGIONAL_LOAD_DESPATCH_CENTRE`), Finance, Telecom entities with 5-component risk breakdowns. |
| **5** | **Review Priority Queue** | Click **REVIEW PRIORITY QUEUE** | 2-pass ranked findings (`GAP-01` Critical SCADA RTU tampering, `GAP-02` Telemetry drop, `GAP-03` Payment switch privilege escalation). |
| **6** | **Evidence Graph Inspection** | Click **SUPERVISORY EVIDENCE GRAPH** | Interactive bipartite graph linking Alerts $\to$ Assets $\to$ Findings $\to$ Threat Intelligence (CISA KEV / MITRE ATT&CK). |
| **7** | **Finding Drill-Down** | Click on finding card or row | Traceable evidence references pointing to raw alert IDs and codified MITRE technique mappings. |
| **8** | **Generate Official Snapshot** | Click **REPORTS & AUDIT TRAIL** $\to$ **Generate Report** | Choose report type (`EXECUTIVE`, `TECHNICAL`, `RISK`, `ASSET`, `VULNERABILITY_THREAT_INTEL`), title, and author. |
| **9** | **Snapshot Immutability** | Click **View** on generated report | Inspect report preview, signed SHA-256 hash badge (`Verified`), and immutable JSON payload. |
| **10** | **Audit Trail Verification** | Click **Audit Trail** $\to$ **Verify Audit Integrity** | Append-only cryptographic hash chain verification passes (`ALL AUDIT TRAIL RECORDS CRYPTOGRAPHICALLY VERIFIED`). |
| **11** | **Tamper Detection Demonstration** | Inject test edit into DB row | UI immediately flags affected report with rose `Tampered` warning badge, proving legal defensibility. |
| **12** | **Point-in-Time DB Backup** | `python scripts/backup_db.py` | Generates `.db` snapshot + `.sha256` sidecar hash in `data/backups/`. |
| **13** | **Network Traffic Audit** | Inspect network connections / wireshark | Confirms **0 external outbound packets** (`127.0.0.1` loopback only). |

---

### Demonstration Timing & Resource Footprint
- **Total Workflow Runtime:** $< 45$ seconds from ingestion to signed report verification.
- **Peak RAM Footprint:** $< 85$ MB.
- **Disk Storage Overhead:** $< 2$ MB per 1,000 multi-CSE alert batches.
