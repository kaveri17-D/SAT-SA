# SAT-SA — Offline Air-Gapped Deployment Guide

## 1. Overview
SAT-SA (Smart Assessment Tool for Security Analytics) is architected for operation in **100% air-gapped, isolated national infrastructure (NCIIPC/CERT-In) supervisory environments**. It operates with **zero runtime external internet dependencies** (`STRICT_LOCAL_ONLY = True`).

---

## 2. System Prerequisites
- **Operating System:** Windows 10/11 / Windows Server 2022 / Linux (Ubuntu 22.04+ / RHEL 9+)
- **Python Runtime:** Python 3.11.x
- **Node.js (Optional / Build-Only):** Node.js 18+ (pre-compiled frontend is included in `frontend/dist`)
- **Memory & Disk:** 4 GB RAM minimum (8 GB recommended for 1M-record graph analysis), 5 GB free disk space.

---

## 3. Offline Deployment Methods

### Method A: Standalone Unified Launcher (Recommended for Field Assessment)
FastAPI serves both the compiled React single-page application at `/` and the REST API at `/api/v1/...` on a single local port.

```powershell
# Windows
.\scripts\start_offline_satsa.bat

# Linux / Unix
chmod +x scripts/start_offline_satsa.sh
./scripts/start_offline_satsa.sh
```
Access the application locally at: `http://127.0.0.1:8000/`

---

### Method B: Offline Container Deployment (Docker / Podman)
If containerization is required:
```powershell
docker-compose up -d --build
```
Ports:
- Unified Backend / API: `http://127.0.0.1:8000`
- Standalone Frontend (if using Nginx container): `http://127.0.0.1:5173`

---

## 4. Operational Health & Readiness Verification
Verify that the service is running and ready:
```powershell
# Run the built-in diagnostic probe CLI
python scripts/health_check.py 8000
```
Expected output:
```json
{
  "status": "ready",
  "service": "SAT-SA — Smart Assessment Tool for Security Analytics",
  "version": "1.0.0",
  "diagnostics": {
    "database": { "status": "healthy", "active_tables": 24 },
    "storage": { "status": "healthy", "free_space_mb": 42512.0 },
    "security": { "airgap_mode": true, "strict_local_only": true, "debug_mode": false }
  }
}
```

---

## 5. Offline Packaging & Distribution
To generate a portable, self-contained offline distribution archive with SHA-256 integrity verification:
```powershell
python packaging/build_offline_package.py
```
This produces a bundle in `dist_offline/satsa_offline_v1.0.0_<timestamp>.zip` with an accompanying `.sha256` sidecar checksum file.
