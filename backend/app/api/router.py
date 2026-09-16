from fastapi import APIRouter

from app.api.routes import analytics, assets, evidence, map_features, real_reports, records


api_router = APIRouter()

api_router.include_router(assets.router)
api_router.include_router(map_features.router)
api_router.include_router(analytics.router)
api_router.include_router(records.router)
api_router.include_router(evidence.router)
api_router.include_router(real_reports.router)
