from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.router import api_router
from app.core.config import settings
from app.db.session import SessionLocal


# ============================================================
# Application lifespan
# ============================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup/shutdown lifecycle.

    Add startup resources here later if required:
    - scheduled ingestion
    - model registry validation
    - cache initialization
    - telemetry workers
    """

    yield


# ============================================================
# FastAPI application
# ============================================================


app = FastAPI(
    title=settings.project_name,
    description=(
        "SIMRAS source-aware API for Andhra Pradesh "
        "infrastructure digital twins, government telemetry, "
        "health prediction, risk assessment and recommendations."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ============================================================
# CORS
# ============================================================
#
# React/Vite may be opened using either:
#
# http://localhost:5173
# http://127.0.0.1:5173
#
# Browsers treat these as DIFFERENT origins.
#
# We therefore explicitly allow both.
# ============================================================


def build_cors_origins() -> list[str]:
    origins: list[str] = []

    configured = getattr(
        settings,
        "cors_origins",
        [],
    )

    # --------------------------------------------------------
    # Accept settings.cors_origins whether it is a list
    # or a comma-separated string.
    # --------------------------------------------------------

    if isinstance(
        configured,
        str,
    ):
        origins.extend(
            item.strip()
            for item in configured.split(",")
            if item.strip()
        )

    elif isinstance(
        configured,
        (
            list,
            tuple,
            set,
        ),
    ):
        origins.extend(
            str(item).strip()
            for item in configured
            if str(item).strip()
        )

    # --------------------------------------------------------
    # Required local development origins
    # --------------------------------------------------------

    local_origins = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ]

    origins.extend(
        local_origins
    )

    # Remove duplicates while preserving order.
    return list(
        dict.fromkeys(
            origins
        )
    )


CORS_ORIGINS = (
    build_cors_origins()
)


app.add_middleware(
    CORSMiddleware,

    allow_origins=(
        CORS_ORIGINS
    ),

    allow_credentials=True,

    # Allow frontend API operations.
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "PATCH",
        "DELETE",
        "OPTIONS",
    ],

    # The frontend currently sends Accept.
    # Using "*" also prevents future browser preflight failures
    # when Content-Type or other normal application headers appear.
    allow_headers=[
        "*",
    ],

    expose_headers=[
        "*",
    ],

    max_age=3600,
)


# ============================================================
# API routes
# ============================================================


app.include_router(
    api_router,
    prefix="/api/v1",
)


# ============================================================
# Root
# ============================================================


@app.get(
    "/",
    tags=["system"],
)
async def root() -> dict[str, str]:
    return {
        "name": (
            settings.project_name
        ),
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1",
    }


# ============================================================
# Health check
# ============================================================


@app.get(
    "/health",
    tags=["system"],
)
async def health() -> dict:
    database = "up"
    database_error = None

    try:
        async with (
            SessionLocal()
            as session
        ):
            await session.execute(
                text(
                    "SELECT 1"
                )
            )

    except Exception as exc:
        database = "down"

        # Do not expose sensitive DB details.
        database_error = (
            exc.__class__.__name__
        )

    status = (
        "ok"
        if database == "up"
        else "degraded"
    )

    response = {
        "status": status,
        "service": (
            settings.project_name
        ),
        "database": database,
        "checked_at": (
            datetime.now(
                UTC
            )
        ),
    }

    if database_error:
        response[
            "database_error"
        ] = database_error

    return response


# ============================================================
# CORS diagnostic
# ============================================================
#
# Useful while debugging frontend/backend connectivity.
# This can remain in development and be removed before deployment.
# ============================================================


@app.get(
    "/debug/cors",
    tags=["system"],
)
async def cors_debug() -> dict:
    return {
        "allowed_origins": (
            CORS_ORIGINS
        ),
        "credentials": True,
        "frontend_expected": (
            "http://localhost:5173"
        ),
    }