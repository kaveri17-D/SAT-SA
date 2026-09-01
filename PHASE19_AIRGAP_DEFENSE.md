# SAT-SA — PHASE 19 AIR-GAP & SOVEREIGN OFFLINE OPERATION DEFENSE

---

### 1. The Strict Local-Only Architecture

```
+-----------------------------------------------------------------------------------+
|                        100% AIR-GAPPED LOCAL SYSTEM BOUNDARY                      |
|                                                                                   |
|  [V] Bundled Python Backend Runtime (FastAPI / SQLAlchemy / SQLite)               |
|  [V] Bundled React 18 Single-Page App (Pre-compiled in frontend/dist)             |
|  [V] Bundled Local Threat Intelligence (CISA KEV, MITRE ATT&CK, NIST NVD)         |
|  [V] Bundled SVG Icons & System Web Fonts (Zero CDN dependencies)                 |
|  [V] Localhost Loopback Communication (127.0.0.1:8000 only)                       |
|                                                                                   |
|  ============================== AIR-GAP BARRIER ================================  |
|                                                                                   |
|  [X] ZERO Remote LLM / AI Model APIs                                              |
|  [X] ZERO Outbound Telemetry or Usage Analytics                                   |
|  [X] ZERO Cloud CDNs or External JavaScript Libraries                             |
|  [X] ZERO External DNS Queries                                                    |
+-----------------------------------------------------------------------------------+
```

---

### 2. Empirical Verification Evidence
- **Verification Method:** Runtime Socket Connect Interception (`socket.socket.connect`).
- **Monitored Scope:** Ingestion, 5-component risk scoring, 2-pass prioritization, evidence graph assembly, report snapshot generation, and native Google Chrome browser automation.
- **Measured External Outbound Network Calls:** **0 (ZERO)**.

---

### 3. Defending Air-Gap Questions

#### Q1: "Why is a strict air-gap requirement non-negotiable for SAT-SA?"
> **Answer:** "National supervisory audits cover critical military command networks, power grid SCADA systems, nuclear infrastructure, and central banking settlement engines. Exporting telemetry or relying on cloud APIs creates immediate national security exposure. SAT-SA runs 100% locally on sovereign field hardware."

#### Q2: "How do you serve the React UI without an internet connection?"
> **Answer:** "FastAPI directly mounts the pre-compiled `frontend/dist/` directory as a static SPA. All CSS, JavaScript bundles, Lucide SVG icons, and system fonts are pre-compiled and served locally over loopback (`127.0.0.1:8000`)."
