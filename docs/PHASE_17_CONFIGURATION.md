# SAT-SA — Production Configuration Guide

## 1. Environment Configuration Variables

SAT-SA uses Pydantic Settings (`BaseSettings`) to manage environment variables from system environment or `.env` file.

| Variable | Default Value | Production Recommendation | Description |
|---|---|---|---|
| `PROJECT_NAME` | `SAT-SA — Smart Assessment Tool for Security Analytics` | Keep default | Supervisory platform name |
| `VERSION` | `1.0.0` | `1.0.0` | Application release version |
| `API_V1_STR` | `/api/v1` | `/api/v1` | API base path prefix |
| `ENVIRONMENT` | `development` | `production` | Production environment flag |
| `DEBUG` | `True` (auto-set `False` in prod) | `False` | Disables debug stack traces in API errors |
| `STRICT_LOCAL_ONLY` | `True` | `True` | Enforces zero external outbound network requests |
| `IS_AIRGAPPED` | `True` | `True` | Enforces local-only model and data foundation operation |
| `DATABASE_URL` | `sqlite:///./satsa_dev.db` | `sqlite:///./satsa_prod.db` or PostgreSQL URI | Active database connection string |
| `SECRET_KEY` | `sat-sa-supervisory-secret-key-change-in-production-airgap` | Set a unique 64-char random string | Symmetric key for signing JWT tokens |
| `ALGORITHM` | `HS256` | `HS256` | JWT signature algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `480` (8 hours) | `480` | Session token validity duration |
| `CORS_ORIGINS` | `["http://localhost:5173", ...]` | Localhost / Intranet origins | Whitelisted origins for API calls |
| `BACKUP_DIR` | `data/backups` | `/var/satsa/backups` or `data/backups` | Directory for point-in-time database backups |

---

## 2. Production Hardening Rules

1. **Production Mode Safeguard:**
   Setting `ENVIRONMENT=production` automatically disables `DEBUG=False` in `Settings`, preventing stack traces or database schema details from leaking in HTTP 500 error responses.

2. **Single-Origin Deployment:**
   FastAPI serves the pre-compiled React SPA assets directly from `frontend/dist`. No reverse proxy (Nginx) or separate web server is required for air-gapped field assessments.

3. **High-Concurrency SQLite WAL Tuning:**
   SQLite is configured with `PRAGMA journal_mode=WAL`, `PRAGMA synchronous=NORMAL`, and `PRAGMA busy_timeout=30000`, supporting concurrent read/write transactions without database lock contention.
