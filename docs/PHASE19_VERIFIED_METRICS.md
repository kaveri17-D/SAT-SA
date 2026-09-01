# SAT-SA — PHASE 19 EMPIRICALLY VERIFIED METRICS TABLE

---

### Master Verified Metrics Catalog

| System Metric | Measured / Evidenced Value | Evidence Source / File Reference | Metric Classification | Verification Status |
|---|---|---|:---:|:---:|
| **Backend Test Suite** | 174 passed, 0 failed, 0 skipped | `pytest app/tests/` execution log | **MEASURED** | **PASS** |
| **Backend Test Duration** | 189.11 seconds | `pytest` runtime timer | **MEASURED** | **PASS** |
| **Frontend Compilation Time** | 1.97 seconds | `npm run build` Vite output | **MEASURED** | **PASS** |
| **Frontend Bundle Size** | 253.68 kB JS, 31.53 kB CSS | `frontend/dist/assets/` | **MEASURED** | **PASS** |
| **Registered API Endpoints** | 27 OpenAPI endpoints | `backend/app/main.py` routing table | **MEASURED** | **PASS** |
| **Database Schema Tables** | 24 relational tables | `Base.metadata.tables` in SQLAlchemy | **MEASURED** | **PASS** |
| **Automated Browser Journeys** | 16 / 16 passed | 10 in Phase 16 + 6 in Phase 18/19 | **MEASURED** | **PASS** |
| **Curated Presentation Screenshots** | 8 standalone images | `data/validation/phase19/presentation/` | **VERIFIED** | **PASS** |
| **Air-Gap External Socket Calls** | Exactly 0 outbound requests | `socket.socket.connect` interceptor log | **MEASURED** | **PASS** |
| **Risk Engine Speed** | 66.69 CSEs / second (22 CSEs in 0.3299s) | `phase19_master_runner.py` log | **MEASURED** | **PASS** |
| **Prioritization Engine Speed** | 39.58 candidates / second | `phase19_master_runner.py` log | **MEASURED** | **PASS** |
| **Demonstration Peak RAM** | 82.4 MB | Python `tracemalloc` tracer | **MEASURED** | **PASS** |
| **1M Benchmark Peak RAM** | ≈ 3.67 GB | Phase 12 Scale Benchmark (`PHASE_12_VALIDATION_REPORT.md`) | **MEASURED** | **PASS** |
| **Cold-Start Launch Latency** | 1.8 seconds | Subprocess timer on `start_offline_satsa.bat` | **MEASURED** | **PASS** |
| **Demonstration Pipeline Duration** | 3.01 seconds | `phase19_master_runner.py` workflow timer | **MEASURED** | **PASS** |
| **Scalability Stress Volume** | 1,000,000 synthetic records | Phase 12 Benchmark report | **MEASURED** | **PASS** |
| **Cryptographic Audit Ledger** | 65 chained records verified unbroken | `AuditService.verify_audit_trail_integrity` | **MEASURED** | **PASS** |
| **Offline Package Size & Files** | 0.34 MB (167 bundled files) | `dist_offline/satsa_offline_v1.0.0_20260901_150521.zip` | **MEASURED** | **PASS** |
| **Offline Package SHA-256** | `8aaeb24de56795a6e1a3c1d9cdbd8fc18a061791ed4dce9400a54e6246ceafc4` | Sidecar `.sha256` checksum calculation | **MEASURED** | **PASS** |
| **Interactive Query Latency** | < 250 ms across all endpoints | Playwright network timing logs | **MEASURED** | **PASS** |
| **20 GB Ingestion Memory** | Constant < 85 MB RAM via 50 MB chunking | Streaming pipeline architecture | **ARCHITECTURAL / ESTIMATED** | **DOCUMENTED** |
| **Enterprise Postgres Scale** | 100+ concurrent examiner sessions | Clustered PostgreSQL connection pool | **ARCHITECTURAL / ESTIMATED** | **DOCUMENTED** |
