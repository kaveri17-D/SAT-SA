import os
import shutil
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.core.database import get_db, Base
from app.core.config import settings

router = APIRouter()


@router.get("/health", summary="System Health & Air-gap Status")
def health_check(db: Session = Depends(get_db)):
    """General supervisory health, version, and air-gap invariant telemetry."""
    db_status = "unhealthy"
    table_count = 0
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
        table_count = len(Base.metadata.tables)
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    return {
        "status": "online" if "healthy" in db_status else "degraded",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "database": db_status,
        "database_tables": table_count,
        "airgap_mode": settings.IS_AIRGAPPED,
        "strict_local_only": settings.STRICT_LOCAL_ONLY,
        "version": settings.VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/health/live", summary="Liveness Probe")
def liveness_check():
    """Lightweight Kubernetes / container orchestrator liveness probe."""
    return {
        "status": "alive",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@router.get("/health/ready", summary="Readiness Probe & Deep Diagnostics")
def readiness_check(db: Session = Depends(get_db)):
    """Comprehensive readiness probe verifying database, tables, storage, and engine health."""
    diagnostics = {}
    is_ready = True

    # 1. Database Connectivity & Query Execution
    try:
        res = db.execute(text("SELECT 1")).scalar()
        diagnostics["database"] = {
            "status": "healthy" if res == 1 else "unexpected_result",
            "active_tables": len(Base.metadata.tables)
        }
    except Exception as e:
        is_ready = False
        diagnostics["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # 2. Disk Storage Availability
    try:
        total, used, free = shutil.disk_usage(os.getcwd())
        free_mb = round(free / (1024 * 1024), 2)
        diagnostics["storage"] = {
            "status": "healthy" if free_mb > 100 else "low_disk_space",
            "free_space_mb": free_mb
        }
    except Exception as e:
        diagnostics["storage"] = {"status": "unknown", "error": str(e)}

    # 3. Air-gap Invariant Check
    diagnostics["security"] = {
        "airgap_mode": settings.IS_AIRGAPPED,
        "strict_local_only": settings.STRICT_LOCAL_ONLY,
        "debug_mode": settings.DEBUG
    }

    if not is_ready:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "diagnostics": diagnostics}
        )

    return {
        "status": "ready",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "diagnostics": diagnostics,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
