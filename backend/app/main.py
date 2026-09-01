from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger
from app.api.routers import health, auth, evidence, risk, prioritization, graph, reports, audit


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Automatic idempotent database bootstrap ensuring schema and baseline rules are initialized on clean boot."""
    try:
        from app.core.database import Base, engine, SessionLocal
        from app.db.seed import seed_baseline_reference_data
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            seed_baseline_reference_data(db)
        finally:
            db.close()
        logger.info("Automatic database schema & baseline reference rules bootstrap complete.")
    except Exception as e:
        logger.warning(f"Startup database bootstrap notice: {str(e)}")
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "SAT-SA (Smart Assessment Tool – Security Analytics) is an offline, "
        "evidence-first supervisory intelligence platform for NCIIPC-style examiners."
    ),
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include core routers
app.include_router(health.router, prefix=settings.API_V1_STR, tags=["System Health"])
app.include_router(auth.router, prefix=f"{settings.API_V1_STR}/auth", tags=["Authentication"])
app.include_router(evidence.router, prefix=f"{settings.API_V1_STR}/evidence", tags=["Evidence Engine"])
app.include_router(risk.router, prefix=f"{settings.API_V1_STR}/risk", tags=["Supervisory Risk Engine"])
app.include_router(prioritization.router, prefix=f"{settings.API_V1_STR}/prioritization", tags=["Review Prioritization Engine"])
app.include_router(graph.router, prefix=settings.API_V1_STR, tags=["Supervisory Evidence Graph Engine"])
app.include_router(reports.router, prefix=f"{settings.API_V1_STR}/reports", tags=["Reporting & Export Engine"])
app.include_router(audit.router, prefix=f"{settings.API_V1_STR}/audit", tags=["Cryptographic Audit Trail Engine"])



import os
from fastapi.staticfiles import StaticFiles

# Mount static frontend production build if present (air-gapped local SPA)
_dist_candidates = [
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")),
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")),
    os.path.abspath("frontend/dist")
]
_mounted = False
for _candidate in _dist_candidates:
    if os.path.isdir(_candidate) and os.path.isfile(os.path.join(_candidate, "index.html")):
        app.mount("/", StaticFiles(directory=_candidate, html=True), name="frontend")
        _mounted = True
        break

if not _mounted:
    @app.get("/", include_in_schema=False)
    def root():
        return {
            "message": "SAT-SA Supervisory Intelligence Platform Backend API",
            "docs": f"{settings.API_V1_STR}/docs",
            "health": f"{settings.API_V1_STR}/health"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
