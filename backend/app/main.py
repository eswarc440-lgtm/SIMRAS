from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import settings
from app.db.session import SessionLocal


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield


from app.api.routes.dam_barrage_profile import router as dam_barrage_profile_router

from app.api.routes.bridge_report_profile import router as bridge_report_profile_router

app = FastAPI(
    title=settings.project_name,
    description="Source-aware API for bridge and dam digital twins",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Admin-API-Key"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
async def root() -> dict[str, str]:
    return {"name": settings.project_name, "docs": "/docs", "health": "/health"}


@app.get("/health")
async def health() -> dict:
    database = "up"
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        database = "down"
    return {
        "status": "ok" if database == "up" else "degraded",
        "service": settings.project_name,
        "database": database,
        "checked_at": datetime.now(UTC),
    }

# SIMRAS_STAGE7_SELECTED_ASSET_REPORTS
from app.api.routes.selected_asset_reports import router as selected_asset_reports_router
from app.api.routes.dam_operational_forecast import router as dam_operational_forecast_router
app.include_router(selected_asset_reports_router, prefix="/api/v1")

# ML-7C official dam/barrage profile route
app.include_router(dam_barrage_profile_router)

# Bridge engineering report profile
app.include_router(bridge_report_profile_router)
app.include_router(dam_operational_forecast_router)
