from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Response
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
async def health(response: Response) -> dict:
    database = "up"
    schema = "ready"
    migration_revision = None
    required_tables_status = "ready"
    overall_status = "ok"

    required_tables = ["assets", "data_sources", "predictions", "inspections", "maintenance"]
    missing_tables = []

    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))

            # Check Alembic revision
            try:
                res = await session.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
                migration_revision = res.scalar()
            except Exception:
                schema = "degraded"
                migration_revision = None

            # Check required tables
            res = await session.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'")
            )
            existing_tables = set(r[0] for r in res.fetchall())
            for t in required_tables:
                if t not in existing_tables:
                    missing_tables.append(t)

            if missing_tables:
                required_tables_status = f"missing: {', '.join(missing_tables)}"
                if "assets" in missing_tables:
                    overall_status = "error"
                    response.status_code = 503
                else:
                    overall_status = "degraded"
            elif not migration_revision:
                schema = "unverified"
                overall_status = "degraded"

    except Exception:
        database = "down"
        schema = "down"
        overall_status = "error"
        response.status_code = 503

    return {
        "status": overall_status,
        "database": database,
        "schema": schema,
        "migration_revision": migration_revision or "unknown",
        "required_tables": required_tables_status,
        "checked_at": datetime.now(UTC).isoformat(),
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
