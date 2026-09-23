from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import get_current_user, get_db
from app.models.entities import Asset
from app.models.operational import Inspection, Maintenance

router = APIRouter(prefix="/gis/operational", tags=["gis-operational"])


@router.get("/inspections")
async def get_inspection_layer(
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Get GIS layer for inspection locations."""
    result = await session.execute(
        select(Inspection)
        .join(Asset)
        .options(joinedload(Inspection.asset))
        .where(Inspection.status.in_(["SCHEDULED", "IN_PROGRESS", "COMPLETED"]))
    )
    inspections = result.scalars().unique().all()

    features = []
    for inspection in inspections:
        if inspection.asset and inspection.asset.representative_geometry:
            features.append({
                "type": "Feature",
                "geometry": inspection.asset.representative_geometry,
                "properties": {
                    "id": inspection.id,
                    "asset_code": inspection.asset_code,
                    "asset_name": inspection.asset.name,
                    "inspection_type": inspection.inspection_type,
                    "status": inspection.status,
                    "priority": inspection.priority,
                    "inspection_date": inspection.inspection_date.isoformat() if inspection.inspection_date else None,
                    "due_date": inspection.due_date.isoformat() if inspection.due_date else None,
                    "overall_condition": inspection.overall_condition,
                    "defect_count": inspection.defect_count,
                },
            })

    return {
        "type": "FeatureCollection",
        "features": features,
    }


@router.get("/maintenance")
async def get_maintenance_layer(
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Get GIS layer for maintenance activity."""
    result = await session.execute(
        select(Maintenance)
        .join(Asset)
        .options(joinedload(Maintenance.asset))
        .where(Maintenance.status.in_(["PROPOSED", "SCHEDULED", "IN_PROGRESS"]))
    )
    maintenance_records = result.scalars().unique().all()

    features = []
    for maintenance in maintenance_records:
        if maintenance.asset and maintenance.asset.representative_geometry:
            features.append({
                "type": "Feature",
                "geometry": maintenance.asset.representative_geometry,
                "properties": {
                    "id": maintenance.id,
                    "asset_code": maintenance.asset_code,
                    "asset_name": maintenance.asset.name,
                    "maintenance_type": maintenance.maintenance_type,
                    "status": maintenance.status,
                    "priority": maintenance.priority,
                    "due_date": maintenance.due_date.isoformat() if maintenance.due_date else None,
                    "progress": maintenance.progress,
                    "estimated_cost": maintenance.estimated_cost,
                },
            })

    return {
        "type": "FeatureCollection",
        "features": features,
    }


@router.get("/plans")
async def get_plans_layer(
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Get GIS layer for action plans."""
    from app.models.operational import AssetPlan

    result = await session.execute(
        select(AssetPlan)
        .join(Asset)
        .options(joinedload(AssetPlan.asset))
        .where(AssetPlan.status.in_(["UNDER_REVIEW", "APPROVED", "IN_PROGRESS"]))
    )
    plans = result.scalars().unique().all()

    features = []
    for plan in plans:
        if plan.asset and plan.asset.representative_geometry:
            features.append({
                "type": "Feature",
                "geometry": plan.asset.representative_geometry,
                "properties": {
                    "id": plan.id,
                    "plan_number": plan.plan_number,
                    "asset_code": plan.asset_code,
                    "asset_name": plan.asset.name,
                    "plan_type": plan.plan_type,
                    "status": plan.status,
                    "priority": plan.priority,
                    "title": plan.title,
                    "estimated_cost": plan.estimated_cost,
                },
            })

    return {
        "type": "FeatureCollection",
        "features": features,
    }


@router.get("/overdue")
async def get_overdue_layer(
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Get GIS layer for overdue inspections and maintenance."""
    from datetime import UTC, datetime

    now = datetime.now(UTC)

    # Overdue inspections
    inspection_result = await session.execute(
        select(Inspection)
        .join(Asset)
        .options(joinedload(Inspection.asset))
        .where(
            Inspection.status.in_(["SCHEDULED", "IN_PROGRESS"]),
            Inspection.due_date < now,
        )
    )
    overdue_inspections = inspection_result.scalars().unique().all()

    # Overdue maintenance
    maintenance_result = await session.execute(
        select(Maintenance)
        .join(Asset)
        .options(joinedload(Maintenance.asset))
        .where(
            Maintenance.status.in_(["SCHEDULED", "IN_PROGRESS"]),
            Maintenance.due_date < now,
        )
    )
    overdue_maintenance = maintenance_result.scalars().unique().all()

    features = []

    for inspection in overdue_inspections:
        if inspection.asset and inspection.asset.representative_geometry:
            features.append({
                "type": "Feature",
                "geometry": inspection.asset.representative_geometry,
                "properties": {
                    "id": inspection.id,
                    "type": "inspection",
                    "asset_code": inspection.asset_code,
                    "asset_name": inspection.asset.name,
                    "status": inspection.status,
                    "due_date": inspection.due_date.isoformat() if inspection.due_date else None,
                    "priority": inspection.priority,
                },
            })

    for maintenance in overdue_maintenance:
        if maintenance.asset and maintenance.asset.representative_geometry:
            features.append({
                "type": "Feature",
                "geometry": maintenance.asset.representative_geometry,
                "properties": {
                    "id": maintenance.id,
                    "type": "maintenance",
                    "asset_code": maintenance.asset_code,
                    "asset_name": maintenance.asset.name,
                    "status": maintenance.status,
                    "due_date": maintenance.due_date.isoformat() if maintenance.due_date else None,
                    "priority": maintenance.priority,
                },
            })

    return {
        "type": "FeatureCollection",
        "features": features,
    }
