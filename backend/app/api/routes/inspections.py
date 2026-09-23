from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_officer, get_current_reviewer, get_current_user, get_db
from app.models.entities import Asset
from app.models.operational import (
    Inspection,
    InspectionAssignment,
    InspectionComponent,
    InspectionDefect,
)
from app.schemas.inspection import (
    InspectionComponentCreate,
    InspectionCreate,
    InspectionDefectCreate,
    InspectionResponse,
    InspectionUpdate,
)

router = APIRouter(prefix="/inspections", tags=["inspections"])


@router.post("", response_model=InspectionResponse, status_code=status.HTTP_201_CREATED)
async def create_inspection(
    inspection_data: InspectionCreate,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_officer),
) -> InspectionResponse:
    """Create a new inspection (OFFICER only)."""
    result = await session.execute(
        select(Asset).where(Asset.asset_code == inspection_data.asset_code)
    )
    asset = result.scalar_one_or_none()

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    inspection = Inspection(
        asset_id=asset.id,
        asset_code=inspection_data.asset_code,
        inspection_date=inspection_data.inspection_date,
        scheduled_date=inspection_data.scheduled_date,
        due_date=inspection_data.due_date,
        inspection_agency=inspection_data.inspection_agency,
        inspection_type=inspection_data.inspection_type,
        assigned_officer=inspection_data.assigned_officer_id,
        priority=inspection_data.priority,
        status="SCHEDULED",
        deck_condition=inspection_data.deck_condition,
        superstructure_condition=inspection_data.superstructure_condition,
        substructure_condition=inspection_data.substructure_condition,
        foundation_condition=inspection_data.foundation_condition,
        scour_condition=inspection_data.scour_condition,
        bearing_condition=inspection_data.bearing_condition,
        joint_condition=inspection_data.joint_condition,
        overall_condition=inspection_data.overall_condition,
        defect_count=inspection_data.defect_count,
        max_defect_severity=inspection_data.max_defect_severity,
        observation=inspection_data.observation,
        recommendation=inspection_data.recommendation,
        created_by=current_user.id,
        verification_status="PENDING_REVIEW",
    )

    session.add(inspection)
    await session.commit()
    await session.refresh(inspection)

    return InspectionResponse.model_validate(inspection)


@router.get("", response_model=list[InspectionResponse])
async def list_inspections(
    status: str | None = None,
    asset_type: str | None = None,
    district: str | None = None,
    priority: str | None = None,
    assigned_to_me: bool = False,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> list[InspectionResponse]:
    """List inspections with filters."""
    query = select(Inspection)

    if status:
        query = query.where(Inspection.status == status)

    if priority:
        query = query.where(Inspection.priority == priority)

    if assigned_to_me and current_user:
        query = query.where(Inspection.assigned_officer == current_user.id)

    if asset_type or district:
        query = query.join(Asset)
        if asset_type:
            query = query.where(Asset.asset_type == asset_type.lower())
        if district:
            query = query.where(Asset.district == district)

    query = query.order_by(Inspection.due_date.asc()).limit(limit).offset(offset)

    result = await session.execute(query)
    inspections = result.scalars().all()

    return [InspectionResponse.model_validate(i) for i in inspections]


@router.get("/current", response_model=list[InspectionResponse])
async def get_current_inspections(
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> list[InspectionResponse]:
    """Get current active inspections."""
    result = await session.execute(
        select(Inspection)
        .where(
            Inspection.status.in_(["SCHEDULED", "IN_PROGRESS"]),
            Inspection.due_date >= datetime.now(UTC),
        )
        .order_by(Inspection.due_date.asc())
    )
    inspections = result.scalars().all()

    return [InspectionResponse.model_validate(i) for i in inspections]


@router.get("/due", response_model=list[InspectionResponse])
async def get_due_inspections(
    days: int = Query(7, ge=1, le=90),
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> list[InspectionResponse]:
    """Get inspections due within specified days."""
    from datetime import timedelta

    due_before = datetime.now(UTC) + timedelta(days=days)

    result = await session.execute(
        select(Inspection)
        .where(
            Inspection.status == "SCHEDULED",
            Inspection.due_date <= due_before,
            Inspection.due_date >= datetime.now(UTC),
        )
        .order_by(Inspection.due_date.asc())
    )
    inspections = result.scalars().all()

    return [InspectionResponse.model_validate(i) for i in inspections]


@router.get("/overdue", response_model=list[InspectionResponse])
async def get_overdue_inspections(
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> list[InspectionResponse]:
    """Get overdue inspections."""
    result = await session.execute(
        select(Inspection)
        .where(
            Inspection.status.in_(["SCHEDULED", "IN_PROGRESS"]),
            Inspection.due_date < datetime.now(UTC),
        )
        .order_by(Inspection.due_date.asc())
    )
    inspections = result.scalars().all()

    return [InspectionResponse.model_validate(i) for i in inspections]


@router.get("/{inspection_id}", response_model=InspectionResponse)
async def get_inspection(
    inspection_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> InspectionResponse:
    """Get inspection by ID."""
    result = await session.execute(
        select(Inspection).where(Inspection.id == inspection_id)
    )
    inspection = result.scalar_one_or_none()

    if inspection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found",
        )

    return InspectionResponse.model_validate(inspection)


@router.put("/{inspection_id}", response_model=InspectionResponse)
async def update_inspection(
    inspection_id: int,
    inspection_data: InspectionUpdate,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_officer),
) -> InspectionResponse:
    """Update inspection (OFFICER only)."""
    result = await session.execute(
        select(Inspection).where(Inspection.id == inspection_id)
    )
    inspection = result.scalar_one_or_none()

    if inspection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found",
        )

    # Update fields
    if inspection_data.started_date is not None:
        inspection.started_date = inspection_data.started_date
    if inspection_data.status is not None:
        inspection.status = inspection_data.status
    if inspection_data.deck_condition is not None:
        inspection.deck_condition = inspection_data.deck_condition
    if inspection_data.superstructure_condition is not None:
        inspection.superstructure_condition = inspection_data.superstructure_condition
    if inspection_data.substructure_condition is not None:
        inspection.substructure_condition = inspection_data.substructure_condition
    if inspection_data.foundation_condition is not None:
        inspection.foundation_condition = inspection_data.foundation_condition
    if inspection_data.scour_condition is not None:
        inspection.scour_condition = inspection_data.scour_condition
    if inspection_data.bearing_condition is not None:
        inspection.bearing_condition = inspection_data.bearing_condition
    if inspection_data.joint_condition is not None:
        inspection.joint_condition = inspection_data.joint_condition
    if inspection_data.overall_condition is not None:
        inspection.overall_condition = inspection_data.overall_condition
    if inspection_data.defect_count is not None:
        inspection.defect_count = inspection_data.defect_count
    if inspection_data.max_defect_severity is not None:
        inspection.max_defect_severity = inspection_data.max_defect_severity
    if inspection_data.observation is not None:
        inspection.observation = inspection_data.observation
    if inspection_data.recommendation is not None:
        inspection.recommendation = inspection_data.recommendation

    inspection.updated_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(inspection)

    return InspectionResponse.model_validate(inspection)


@router.post("/{inspection_id}/submit")
async def submit_inspection(
    inspection_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_officer),
) -> dict[str, str]:
    """Submit inspection for review (OFFICER only)."""
    result = await session.execute(
        select(Inspection).where(Inspection.id == inspection_id)
    )
    inspection = result.scalar_one_or_none()

    if inspection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found",
        )

    if inspection.status == "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inspection already completed",
        )

    inspection.status = "COMPLETED"
    inspection.updated_at = datetime.now(UTC)

    await session.commit()

    return {"message": "Inspection submitted for review"}


@router.post("/{inspection_id}/review")
async def review_inspection(
    inspection_id: int,
    approved: bool,
    remarks: str | None = None,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_reviewer),
) -> dict[str, str]:
    """Review inspection (REVIEWER/ADMIN only)."""
    result = await session.execute(
        select(Inspection).where(Inspection.id == inspection_id)
    )
    inspection = result.scalar_one_or_none()

    if inspection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found",
        )

    if inspection.status != "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inspection must be completed before review",
        )

    if approved:
        inspection.verification_status = "APPROVED"
        inspection.status = "APPROVED"
    else:
        inspection.verification_status = "REVISION_REQUIRED"
        inspection.status = "REVISION_REQUIRED"

    inspection.reviewed_by = current_user.id
    inspection.updated_at = datetime.now(UTC)

    await session.commit()

    return {"message": f"Inspection {'approved' if approved else 'rejected'}"}


@router.post("/{inspection_id}/components", status_code=status.HTTP_201_CREATED)
async def add_inspection_component(
    inspection_id: int,
    component_data: InspectionComponentCreate,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_officer),
) -> dict[str, str]:
    """Add component to inspection (OFFICER only)."""
    result = await session.execute(
        select(Inspection).where(Inspection.id == inspection_id)
    )
    inspection = result.scalar_one_or_none()

    if inspection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found",
        )

    component = InspectionComponent(
        inspection_id=inspection_id,
        component_name=component_data.component_name,
        component_type=component_data.component_type,
        condition=component_data.condition,
        observation=component_data.observation,
        evidence=component_data.evidence,
    )

    session.add(component)
    await session.commit()

    return {"message": "Component added"}


@router.post("/{inspection_id}/defects", status_code=status.HTTP_201_CREATED)
async def add_inspection_defect(
    inspection_id: int,
    defect_data: InspectionDefectCreate,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_officer),
) -> dict[str, str]:
    """Add defect to inspection (OFFICER only)."""
    result = await session.execute(
        select(Inspection).where(Inspection.id == inspection_id)
    )
    inspection = result.scalar_one_or_none()

    if inspection is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found",
        )

    defect = InspectionDefect(
        inspection_id=inspection_id,
        defect_type=defect_data.defect_type,
        severity=defect_data.severity,
        measurement=defect_data.measurement,
        location=defect_data.location,
        observation=defect_data.observation,
        recommendation=defect_data.recommendation,
    )

    session.add(defect)
    await session.commit()

    return {"message": "Defect added"}
