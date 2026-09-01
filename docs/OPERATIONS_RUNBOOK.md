# SAT-SA — Operations Runbook & Examiner Manual

## 1. System Startup & Verification
```powershell
# 1. Start Platform
.\scripts\start_offline_satsa.bat

# 2. Run Health & Readiness Diagnostic Probe
python scripts/health_check.py 8000

# 3. Access Web Interface in Chrome
Start-Process "http://127.0.0.1:8000/"
```

---

## 2. Standard Examiner Workflows

### 2.1 Ingesting & Analyzing Telemetry
1. Open **Supervisory Dashboard** at `http://127.0.0.1:8000/`.
2. Inspect active critical security entities (CSEs) and real-time supervisory risk score distributions.
3. Review anomalous alerts in the **Review Priority Queue**.

### 2.2 Generating & Signing Official Assessment Reports
1. Navigate to **Reports & Audit Trail** (`/reports`).
2. Click **Generate Report**.
3. Select Report Type:
   - `EXECUTIVE`: High-level posture, CSE risk bands, critical gaps.
   - `TECHNICAL`: Full finding breakdowns, rules triggered, recommendations.
   - `RISK`: 5-component risk breakdown (Execution Gap, Negative Space, Peer Deviation, Anomaly, Criticality).
   - `ASSET`: Asset vulnerability profiling and KEV exposure matrix.
   - `VULNERABILITY_THREAT_INTEL`: MITRE ATT&CK and threat intelligence cross-references.
4. Provide Assessment Title and click **Generate Assessment Report Snapshot**.
5. The generated report snapshot is immutably sealed with SHA-256 and linked to the cryptographic audit trail ledger.

### 2.3 Cryptographic Audit Ledger Verification
1. In the **Reports & Audit Trail** view, switch to the **Audit Trail** sub-tab.
2. Click **Verify Audit Integrity**.
3. The system scans the append-only cryptographic hash chain and displays `ALL AUDIT TRAIL RECORDS CRYPTOGRAPHICALLY VERIFIED`.

---

## 3. Routine Maintenance & Database Backups
```powershell
# Create scheduled point-in-time database backup
python scripts/backup_db.py data/backups
```

---

## 4. Troubleshooting & Failure Recovery

| Symptom | Probable Cause | Corrective Action |
|---|---|---|
| Health check returns 503 | Database locked or uninitialized | Check disk space; run `python scripts/health_check.py` to inspect diagnostics. |
| UI shows `Tampered` badge | Unauthorized database row modification | Report has been altered post-signature. Re-verify audit trail or restore from backup. |
| Audit verification returns mismatch | Interrupted or tampered audit row | Inspect audit log row details to identify the broken link in the hash chain. |
