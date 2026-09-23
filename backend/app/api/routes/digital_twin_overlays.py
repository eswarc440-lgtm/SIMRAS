from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.api.deps import get_current_user, get_db
from app.models.entities import Asset
from app.models.operational import Inspection, InspectionDefect, Maintenance

router = APIRouter(prefix="/digital-twin/{asset_code}/overlays", tags=["digital-twin-overlays"])


@router.get("/inspections")
async def get_inspection_overlays(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Get inspection overlays for digital twin."""
    result = await session.execute(
        select(Asset).where(Asset.asset_code == asset_code)
    )
    asset = result.scalar_one_or_none()

    if not asset:
        return {"overlays": []}

    result = await session.execute(
        select(Inspection)
        .where(Inspection.asset_id == asset.id)
        .order_by(Inspection.inspection_date.desc())
    )
    inspections = result.scalars().all()

    overlays = []
    for inspection in inspections:
        overlay = {
            "id": inspection.id,
            "type": "inspection",
            "date": inspection.inspection_date.isoformat() if inspection.inspection_date else None,
            "status": inspection.status,
            "inspection_type": inspection.inspection_type,
            "overall_condition": inspection.overall_condition,
            "defect_count": inspection.defect_count,
            "max_defect_severity": inspection.max_defect_severity,
            "priority": inspection.priority,
            "components": [],
            "defects": [],
        }

        # Get components
        from app.models.operational import InspectionComponent

        component_result = await session.execute(
            select(InspectionComponent).where(InspectionComponent.inspection_id == inspection.id)
        )
        components = component_result.scalars().all()

        for component in components:
            overlay["components"].append({
                "id": component.id,
                "name": component.component_name,
                "type": component.component_type,
                "condition": component.condition,
                "observation": component.observation,
            })

        # Get defects
        defect_result = await session.execute(
            select(InspectionDefect).where(InspectionDefect.inspection_id == inspection.id)
        )
        defects = defect_result.scalars().all()

        for defect in defects:
            overlay["defects"].append({
                "id": defect.id,
                "type": defect.defect_type,
                "severity": defect.severity,
                "location": defect.location,
                "observation": defect.observation,
                "recommendation": defect.recommendation,
            })

        overlays.append(overlay)

    return {"overlays": overlays}


@router.get("/maintenance")
async def get_maintenance_overlays(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Get maintenance overlays for digital twin."""
    result = await session.execute(
        select(Asset).where(Asset.asset_code == asset_code)
    )
    asset = result.scalar_one_or_none()

    if not asset:
        return {"overlays": []}

    result = await session.execute(
        select(Maintenance)
        .where(Maintenance.asset_id == asset.id)
        .order_by(Maintenance.created_at.desc())
    )
    maintenance_records = result.scalars().all()

    overlays = []
    for maintenance in maintenance_records:
        overlay = {
            "id": maintenance.id,
            "type": "maintenance",
            "maintenance_type": maintenance.maintenance_type,
            "component": maintenance.component,
            "status": maintenance.status,
            "priority": maintenance.priority,
            "problem": maintenance.problem,
            "proposed_action": maintenance.proposed_action,
            "start_date": maintenance.start_date.isoformat() if maintenance.start_date else None,
            "due_date": maintenance.due_date.isoformat() if maintenance.due_date else None,
            "completion_date": maintenance.completion_date.isoformat() if maintenance.completion_date else None,
            "progress": maintenance.progress,
            "estimated_cost": maintenance.estimated_cost,
            "actual_cost": maintenance.actual_cost,
        }

        overlays.append(overlay)

    return {"overlays": overlays}


@router.get("/plans")
async def get_plan_overlays(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Get action plan overlays for digital twin."""
    from app.models.operational import AssetPlan

    result = await session.execute(
        select(Asset).where(Asset.asset_code == asset_code)
    )
    asset = result.scalar_one_or_none()

    if not asset:
        return {"overlays": []}

    result = await session.execute(
        select(AssetPlan)
        .where(AssetPlan.asset_id == asset.id)
        .order_by(AssetPlan.created_at.desc())
    )
    plans = result.scalars().all()

    overlays = []
    for plan in plans:
        overlay = {
            "id": plan.id,
            "type": "plan",
            "plan_number": plan.plan_number,
            "plan_type": plan.plan_type,
            "title": plan.title,
            "status": plan.status,
            "priority": plan.priority,
            "problem_identified": plan.problem_identified,
            "proposed_action": plan.proposed_action,
            "affected_components": plan.affected_components,
            "proposed_start": plan.proposed_start.isoformat() if plan.proposed_start else None,
            "proposed_end": plan.proposed_end.isoformat() if plan.proposed_end else None,
            "estimated_cost": plan.estimated_cost,
        }

        overlays.append(overlay)

    return {"overlays": overlays}


@router.get("/workflow-state")
async def get_workflow_state(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, Any]:
    """Get complete workflow state for digital twin overlay."""
    result = await session.execute(
        select(Asset).where(Asset.asset_code == asset_code)
    )
    asset = result.scalar_one_or_none()

    if not asset:
        return {"state": "ASSET_NOT_FOUND"}

    # Get latest inspection
    inspection_result = await session.execute(
        select(Inspection)
        .where(Inspection.asset_id == asset.id)
        .order_by(Inspection.inspection_date.desc())
        .limit(1)
    )
    latest_inspection = inspection_result.scalar_one_or_none()

    # Get active maintenance
    maintenance_result = await session.execute(
        select(Maintenance)
        .where(
            Maintenance.asset_id == asset.id,
            Maintenance.status.in_(["SCHEDULED", "IN_PROGRESS"]),
        )
        .order_by(Maintenance.due_date.asc())
    )
    active_maintenance = maintenance_result.scalars().all()

    # Get active plans
    from app.models.operational import AssetPlan

    plan_result = await session.execute(
        select(AssetPlan)
        .where(
            AssetPlan.asset_id == asset.id,
            AssetPlan.status.in_(["UNDER_REVIEW", "APPROVED", "IN_PROGRESS"]),
        )
        .order_by(AssetPlan.created_at.desc())
    )
    active_plans = plan_result.scalars().all()

    return {
        "state": "WORKFLOW_ACTIVE",
        "asset": {
            "asset_code": asset.asset_code,
            "name": asset.name,
            "identity_status": asset.identity_status,
        },
        "latest_inspection": {
            "id": latest_inspection.id,
            "date": latest_inspection.inspection_date.isoformat() if latest_inspection and latest_inspection.inspection_date else None,
            "status": latest_inspection.status if latest_inspection else None,
            "overall_condition": latest_inspection.overall_condition if latest_inspection else None,
        } if latest_inspection else None,
        "active_maintenance": [
            {
                "id": m.id,
                "type": m.maintenance_type,
                "status": m.status,
                "due_date": m.due_date.isoformat() if m.due_date else None,
                "progress": m.progress,
            }
            for m in active_maintenance
        ],
        "active_plans": [
            {
                "id": p.id,
                "plan_number": p.plan_number,
                "type": p.plan_type,
                "status": p.status,
                "title": p.title,
            }
            for p in active_plans
        ],
    }
