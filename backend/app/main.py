from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger
from app.api.routers import health, auth, evidence, risk, prioritization, graph

app = FastAPI(
    title=settings.PROJECT_NAME,
    description=(
        "SAT-SA (Smart Assessment Tool – Security Analytics) is an offline, "
        "evidence-first supervisory intelligence platform for NCIIPC-style examiners."
    ),
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc"
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
