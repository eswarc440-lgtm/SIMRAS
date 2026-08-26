from fastapi import APIRouter

from app.api.routes import analytics, assets, records

api_router = APIRouter()
api_router.include_router(assets.router)
api_router.include_router(analytics.router)
api_router.include_router(records.router)
