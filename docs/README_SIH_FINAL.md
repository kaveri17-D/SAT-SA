# SAT-SA — Smart Assessment Tool for Security Analytics
## Sovereign Supervisory Intelligence Platform for Critical Security Entities (CSEs)
### Smart India Hackathon (SIH) — Problem Statement 26157

---

### Executive Overview
**SAT-SA** is a 100% sovereign, air-gapped supervisory security analytics platform designed for national cybersecurity regulators (NCIIPC, CERT-In) and sectoral examiners (RBI, CEA, TRAI). It evaluates the **integrity, completeness, and risk** of cyber defense operations across multi-sector Critical Security Entities (Power Grid, Banking Core, Telecom).

Unlike traditional SIEM/SOAR tools that operate *inside* a single enterprise perimeter, SAT-SA operates at the **supervisory tier** to detect:
1. **SOC Execution Gaps (`GAP-01`..`GAP-06`):** Untriaged critical alerts, hasty closures, and unjustified false-positive markdowns.
2. **Negative Space Anomalies (`NEG-01`..`NEG-04`):** Sensor telemetry drops, agent tampering, and logging blind spots.
3. **Decomposable 5-Component Risk:** Explainable mathematical risk formulation replacing black-box AI.
4. **2-Pass Diversity Prioritization:** Prevents noisy entities from monopolizing national examiner bandwidth.
5. **Cryptographic Legal Auditability:** Canonical SHA-256 report snapshots and genesis-anchored append-only audit chains with real-time UI tamper detection.

---

### Quick Start (Offline Deployment)

#### 1. Launch Platform
```powershell
# Windows
.\scripts\start_offline_satsa.bat

# Linux / Unix
chmod +x scripts/start_offline_satsa.sh
./scripts/start_offline_satsa.sh
```
Access the examiner interface locally at: **`http://127.0.0.1:8000/`**

#### 2. Verify Health & Diagnostics
```powershell
python scripts/health_check.py 8000
```
Expected output: HTTP 200 `status: ready`, 24 DB tables active, `airgap_mode: true`.

#### 3. Run Automated Regression Suite
```powershell
cd backend
python -m pytest app/tests/ -v
```
All **174 test cases** pass with 0 failures in $< 2.5$ minutes.

---

### Key Presentation & Audit Artifacts
- **Final System Certification:** [`PHASE19_FINAL_SYSTEM_CERTIFICATION.md`](file:///c:/Users/LENOVO/SAT-SA/PHASE19_FINAL_SYSTEM_CERTIFICATION.md)
- **SIH Problem Statement Alignment:** [`PHASE19_SIH_PROBLEM_ALIGNMENT.md`](file:///c:/Users/LENOVO/SAT-SA/PHASE19_SIH_PROBLEM_ALIGNMENT.md)
- **Technical Architecture Manual:** [`PHASE19_FINAL_ARCHITECTURE.md`](file:///c:/Users/LENOVO/SAT-SA/PHASE19_FINAL_ARCHITECTURE.md)
- **Master 39-Question Judge Q&A:** [`PHASE19_JUDGE_QA.md`](file:///c:/Users/LENOVO/SAT-SA/PHASE19_JUDGE_QA.md)
- **Hostile Judge Attack Review:** [`PHASE19_JUDGE_ATTACK_REVIEW.md`](file:///c:/Users/LENOVO/SAT-SA/PHASE19_JUDGE_ATTACK_REVIEW.md)
- **15-Slide Presentation Deck:** [`PHASE19_SIH_PPT_CONTENT.md`](file:///c:/Users/LENOVO/SAT-SA/PHASE19_SIH_PPT_CONTENT.md)
- **SIH Live Demonstration Script:** [`PHASE19_FINAL_SIH_DEMO_SCRIPT.md`](file:///c:/Users/LENOVO/SAT-SA/PHASE19_FINAL_SIH_DEMO_SCRIPT.md)
- **Curated Presentation Screenshots:** `data/validation/phase19/presentation/`
- **Offline Release Archive:** [`dist_offline/satsa_offline_v1.0.0_20260901_143526.zip`](file:///c:/Users/LENOVO/SAT-SA/dist_offline/satsa_offline_v1.0.0_20260901_143526.zip)
