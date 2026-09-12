from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import require_admin_key
from app.db.session import get_db
from app.models.entities import Alert, Asset, DataSource, Inspection, Maintenance, Prediction
from app.schemas.records import AlertAction, AlertCreate, InspectionCreate, MaintenanceCreate
from app.services.twin_service import refresh_ml_prediction

router = APIRouter(tags=["operations"])


async def _asset(session: AsyncSession, asset_code: str) -> Asset:
    asset = await session.scalar(select(Asset).where(Asset.asset_code == asset_code))
    if asset is None:
        raise HTTPException(status_code=404, detail=f"Asset {asset_code} was not found")
    return asset


async def _manual_source(session: AsyncSession) -> DataSource:
    source = await session.scalar(
        select(DataSource).where(DataSource.code == "MANUAL_APPROVED_ENTRY")
    )
    if source:
        return source
    source = DataSource(
        code="MANUAL_APPROVED_ENTRY",
        name="Approved SIMRAS operator entry",
        organisation="SIMRAS",
        source_type="MANUAL_APPROVED",
        refresh_policy="On approved change",
        is_authoritative=False,
    )
    session.add(source)
    await session.flush()
    return source


@router.get("/assets/{asset_code}/inspections")
async def list_inspections(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    asset = await _asset(session, asset_code)
    rows = (
        await session.execute(
            select(Inspection)
            .where(Inspection.asset_id == asset.id)
            .order_by(desc(Inspection.inspection_date))
        )
    ).scalars().all()
    return [
        {
            "id": row.id,
            "date": row.inspection_date,
            "type": row.inspection_type,
            "condition": row.condition,
            "score": row.score,
            "quality_flag": row.quality_flag,
            "is_synthetic": row.is_synthetic,
        }
        for row in rows
    ]


@router.post("/inspections", dependencies=[Depends(require_admin_key)], status_code=201)
async def create_inspection(
    payload: InspectionCreate,
    session: AsyncSession = Depends(get_db),
) -> dict:
    asset = await _asset(session, payload.asset_code)
    source = await _manual_source(session)
    inspection = Inspection(
        asset_id=asset.id,
        inspection_date=payload.inspection_date,
        inspection_type=payload.inspection_type,
        condition=payload.condition,
        score=payload.score,
        inspector=payload.inspector,
        notes=payload.notes,
        source_id=source.id,
        quality_flag="OPERATOR_ENTERED",
        is_synthetic=False,
    )
    session.add(inspection)
    await session.commit()
    await session.refresh(inspection)
    return {"id": inspection.id, "status": "created"}


@router.get("/assets/{asset_code}/maintenance")
async def list_maintenance(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    asset = await _asset(session, asset_code)
    rows = (
        await session.execute(
            select(Maintenance)
            .where(Maintenance.asset_id == asset.id)
            .order_by(desc(Maintenance.maintenance_date))
        )
    ).scalars().all()
    return [
        {
            "id": row.id,
            "date": row.maintenance_date,
            "action": row.action,
            "status": row.status,
            "next_due": row.next_due,
            "is_synthetic": row.is_synthetic,
        }
        for row in rows
    ]


@router.post("/maintenance", dependencies=[Depends(require_admin_key)], status_code=201)
async def create_maintenance(
    payload: MaintenanceCreate,
    session: AsyncSession = Depends(get_db),
) -> dict:
    asset = await _asset(session, payload.asset_code)
    source = await _manual_source(session)
    record = Maintenance(
        asset_id=asset.id,
        maintenance_date=payload.maintenance_date,
        action=payload.action,
        status=payload.status,
        next_due=payload.next_due,
        cost=payload.cost,
        source_id=source.id,
        is_synthetic=False,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return {"id": record.id, "status": "created"}
@router.post(
    "/assets/{asset_code}/predictions/refresh",
    dependencies=[Depends(require_admin_key)],
)
async def refresh_asset_prediction(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """
    Run the accepted ML model for an asset and persist
    the resulting health, risk and RUL predictions.
    """

    return await refresh_ml_prediction(
        session=session,
        asset_code=asset_code,
    )

@router.get("/assets/{asset_code}/predictions/history")
async def prediction_history(
    asset_code: str,
    target: str | None = Query(default=None),
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    asset = await _asset(session, asset_code)
    statement = select(Prediction).where(Prediction.asset_id == asset.id)
    if target:
        statement = statement.where(Prediction.target == target)
    rows = (await session.execute(statement.order_by(desc(Prediction.prediction_time)))).scalars()
    return [
        {
            "target": row.target,
            "value": row.value,
            "class": row.predicted_class,
            "time": row.prediction_time,
            "model_version": row.model_version,
            "feature_version": row.feature_version,
            "confidence": row.confidence_score,
            "status": row.status,
        }
        for row in rows
    ]


@router.get("/alerts")
async def list_alerts(
    active_only: bool = True,
    session: AsyncSession = Depends(get_db),
) -> list[dict]:
    statement = select(Alert, Asset.asset_code, Asset.name).join(Asset, Asset.id == Alert.asset_id)
    if active_only:
        statement = statement.where(Alert.resolved_at.is_(None))
    rows = (await session.execute(statement.order_by(desc(Alert.created_at_event)))).all()
    return [
        {
            "id": alert.id,
            "asset_code": asset_code,
            "asset_name": asset_name,
            "severity": alert.severity,
            "rule": alert.rule,
            "message": alert.message,
            "created_at": alert.created_at_event,
            "acknowledged_at": alert.acknowledged_at,
            "resolved_at": alert.resolved_at,
        }
        for alert, asset_code, asset_name in rows
    ]


@router.post("/alerts", dependencies=[Depends(require_admin_key)], status_code=201)
async def create_alert(
    payload: AlertCreate,
    session: AsyncSession = Depends(get_db),
) -> dict:
    asset = await _asset(session, payload.asset_code)
    alert = Alert(
        asset_id=asset.id,
        severity=payload.severity,
        rule=payload.rule,
        message=payload.message,
        created_at_event=datetime.now(UTC),
    )
    session.add(alert)
    await session.commit()
    await session.refresh(alert)
    return {"id": alert.id, "status": "created"}


@router.patch("/alerts/{alert_id}", dependencies=[Depends(require_admin_key)])
async def update_alert(
    alert_id: int,
    payload: AlertAction,
    session: AsyncSession = Depends(get_db),
) -> dict:
    alert = await session.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert was not found")
    now = datetime.now(UTC)
    if payload.action == "ACKNOWLEDGE":
        alert.acknowledged_at = now
    else:
        alert.resolved_at = now
        alert.acknowledged_at = alert.acknowledged_at or now
    await session.commit()
    return {"id": alert.id, "status": payload.action.lower()}

