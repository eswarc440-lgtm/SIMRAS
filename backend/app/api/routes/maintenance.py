from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_officer, get_current_reviewer, get_current_user, get_db
from app.models.entities import Asset
from app.models.operational import Maintenance
from app.schemas.maintenance import (
    MaintenanceCreate,
    MaintenanceResponse,
    MaintenanceUpdate,
)

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


@router.post("", response_model=MaintenanceResponse, status_code=status.HTTP_201_CREATED)
async def create_maintenance(
    maintenance_data: MaintenanceCreate,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_officer),
) -> MaintenanceResponse:
    """Create a new maintenance record (OFFICER only)."""
    result = await session.execute(
        select(Asset).where(Asset.asset_code == maintenance_data.asset_code)
    )
    asset = result.scalar_one_or_none()

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    maintenance = Maintenance(
        asset_id=asset.id,
        asset_code=maintenance_data.asset_code,
        maintenance_type=maintenance_data.maintenance_type,
        component=maintenance_data.component,
        priority=maintenance_data.priority,
        status="PROPOSED",
        problem=maintenance_data.problem,
        reason=maintenance_data.reason,
        proposed_action=maintenance_data.proposed_action,
        assigned_department=maintenance_data.assigned_department,
        contractor=maintenance_data.contractor,
        estimated_cost=maintenance_data.estimated_cost,
        start_date=maintenance_data.start_date,
        due_date=maintenance_data.due_date,
        progress=0,
        created_by=current_user.id,
        verification_status="PENDING_REVIEW",
    )

    session.add(maintenance)
    await session.commit()
    await session.refresh(maintenance)

    return MaintenanceResponse.model_validate(maintenance)


@router.get("", response_model=list[MaintenanceResponse])
async def list_maintenance(
    status: str | None = None,
    asset_type: str | None = None,
    priority: str | None = None,
    assigned_to_me: bool = False,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> list[MaintenanceResponse]:
    """List maintenance records with filters."""
    query = select(Maintenance)

    if status:
        query = query.where(Maintenance.status == status)

    if priority:
        query = query.where(Maintenance.priority == priority)

    if asset_type:
        query = query.join(Asset).where(Asset.asset_type == asset_type.lower())

    query = query.order_by(Maintenance.due_date.asc()).limit(limit).offset(offset)

    result = await session.execute(query)
    maintenance_records = result.scalars().all()

    return [MaintenanceResponse.model_validate(m) for m in maintenance_records]


@router.get("/current", response_model=list[MaintenanceResponse])
async def get_current_maintenance(
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> list[MaintenanceResponse]:
    """Get current active maintenance."""
    result = await session.execute(
        select(Maintenance)
        .where(
            Maintenance.status.in_(["SCHEDULED", "IN_PROGRESS"]),
            Maintenance.due_date >= datetime.now(UTC),
        )
        .order_by(Maintenance.due_date.asc())
    )
    maintenance_records = result.scalars().all()

    return [MaintenanceResponse.model_validate(m) for m in maintenance_records]


@router.get("/overdue", response_model=list[MaintenanceResponse])
async def get_overdue_maintenance(
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> list[MaintenanceResponse]:
    """Get overdue maintenance."""
    result = await session.execute(
        select(Maintenance)
        .where(
            Maintenance.status.in_(["SCHEDULED", "IN_PROGRESS"]),
            Maintenance.due_date < datetime.now(UTC),
        )
        .order_by(Maintenance.due_date.asc())
    )
    maintenance_records = result.scalars().all()

    return [MaintenanceResponse.model_validate(m) for m in maintenance_records]


@router.get("/{maintenance_id}", response_model=MaintenanceResponse)
async def get_maintenance(
    maintenance_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> MaintenanceResponse:
    """Get maintenance by ID."""
    result = await session.execute(
        select(Maintenance).where(Maintenance.id == maintenance_id)
    )
    maintenance = result.scalar_one_or_none()

    if maintenance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance not found",
        )

    return MaintenanceResponse.model_validate(maintenance)


@router.put("/{maintenance_id}", response_model=MaintenanceResponse)
async def update_maintenance(
    maintenance_id: int,
    maintenance_data: MaintenanceUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_officer),
) -> MaintenanceResponse:
    """Update maintenance (OFFICER only)."""
    result = await session.execute(
        select(Maintenance).where(Maintenance.id == maintenance_id)
    )
    maintenance = result.scalar_one_or_none()

    if maintenance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance not found",
        )

    # Update fields
    if maintenance_data.status is not None:
        maintenance.status = maintenance_data.status
    if maintenance_data.progress is not None:
        maintenance.progress = maintenance_data.progress
    if maintenance_data.actual_cost is not None:
        maintenance.actual_cost = maintenance_data.actual_cost
    if maintenance_data.completion_date is not None:
        maintenance.completion_date = maintenance_data.completion_date

    maintenance.updated_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(maintenance)

    return MaintenanceResponse.model_validate(maintenance)


@router.post("/{maintenance_id}/progress")
async def update_maintenance_progress(
    maintenance_id: int,
    progress_percentage: int = Query(..., ge=0, le=100),
    notes: str | None = None,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_officer),
) -> dict[str, str]:
    """Update maintenance progress (OFFICER only)."""
    result = await session.execute(
        select(Maintenance).where(Maintenance.id == maintenance_id)
    )
    maintenance = result.scalar_one_or_none()

    if maintenance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance not found",
        )

    maintenance.progress = progress_percentage
    maintenance.updated_at = datetime.now(UTC)

    if progress_percentage == 100:
        maintenance.status = "COMPLETED"
        maintenance.completion_date = datetime.now(UTC)

    await session.commit()

    return {"message": "Progress updated"}


@router.post("/{maintenance_id}/complete")
async def complete_maintenance(
    maintenance_id: int,
    actual_cost: int | None = None,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_officer),
) -> dict[str, str]:
    """Mark maintenance as complete (OFFICER only)."""
    result = await session.execute(
        select(Maintenance).where(Maintenance.id == maintenance_id)
    )
    maintenance = result.scalar_one_or_none()

    if maintenance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance not found",
        )

    maintenance.status = "COMPLETED"
    maintenance.progress = 100
    maintenance.completion_date = datetime.now(UTC)
    if actual_cost is not None:
        maintenance.actual_cost = actual_cost
    maintenance.updated_at = datetime.now(UTC)

    await session.commit()

    return {"message": "Maintenance marked as complete"}


@router.post("/{maintenance_id}/review")
async def review_maintenance(
    maintenance_id: int,
    approved: bool,
    remarks: str | None = None,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_reviewer),
) -> dict[str, str]:
    """Review maintenance completion (REVIEWER/ADMIN only)."""
    result = await session.execute(
        select(Maintenance).where(Maintenance.id == maintenance_id)
    )
    maintenance = result.scalar_one_or_none()

    if maintenance is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance not found",
        )

    if maintenance.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maintenance must be completed before review",
        )

    if approved:
        maintenance.verification_status = "VERIFIED_COMPLETE"
    else:
        maintenance.verification_status = "REVISION_REQUIRED"

    maintenance.reviewed_by = current_user.id
    maintenance.updated_at = datetime.now(UTC)

    await session.commit()

    return {"message": f"Maintenance {'verified' if approved else 'rejected'}"}
