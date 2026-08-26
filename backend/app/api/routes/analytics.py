from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.entities import Alert, Asset, EnvironmentObservation, Prediction

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
async def summary(session: AsyncSession = Depends(get_db)) -> dict:
    assets = await session.scalar(select(func.count()).select_from(Asset))
    bridges = await session.scalar(
        select(func.count()).select_from(Asset).where(Asset.asset_type == "bridge")
    )
    water_assets = await session.scalar(
        select(func.count())
        .select_from(Asset)
        .where(Asset.asset_type.in_(["dam", "barrage"]))
    )
    predictions = await session.scalar(select(func.count()).select_from(Prediction))
    active_alerts = await session.scalar(
        select(func.count()).select_from(Alert).where(Alert.resolved_at.is_(None))
    )
    return {
        "assets": assets or 0,
        "bridges": bridges or 0,
        "dams_and_barrages": water_assets or 0,
        "predictions": predictions or 0,
        "active_alerts": active_alerts or 0,
    }


@router.get("/freshness")
async def freshness(session: AsyncSession = Depends(get_db)) -> dict:
    latest_environment = await session.scalar(select(func.max(EnvironmentObservation.observed_at)))
    latest_prediction = await session.scalar(select(func.max(Prediction.prediction_time)))
    return {
        "environment_latest": latest_environment,
        "prediction_latest": latest_prediction,
    }

