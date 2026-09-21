from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_officer, get_current_reviewer, get_current_user, get_db
from app.models.entities import Asset
from app.models.operational import AssetPlan
from app.schemas.plans import PlanCreate, PlanResponse

router = APIRouter(prefix="/plans", tags=["plans"])


@router.post("", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan(
    plan_data: PlanCreate,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_officer),
) -> PlanResponse:
    """Create a new action plan (OFFICER only)."""
    result = await session.execute(
        select(Asset).where(Asset.asset_code == plan_data.asset_code)
    )
    asset = result.scalar_one_or_none()

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    # Generate plan number
    result = await session.execute(
        select(AssetPlan).order_by(AssetPlan.id.desc()).limit(1)
    )
    last_plan = result.scalar_one_or_none()
    sequence = (last_plan.id + 1) if last_plan else 1
    plan_number = f"PLAN-{datetime.now(UTC).year}-{sequence:04d}"

    plan = AssetPlan(
        plan_number=plan_number,
        asset_id=asset.id,
        asset_code=plan_data.asset_code,
        plan_type=plan_data.plan_type,
        title=plan_data.title,
        description=plan_data.description,
        priority=plan_data.priority,
        problem_identified=plan_data.problem_identified,
        evidence=plan_data.evidence,
        proposed_action=plan_data.proposed_action,
        affected_components=plan_data.affected_components,
        proposed_start=plan_data.proposed_start,
        proposed_end=plan_data.proposed_end,
        estimated_cost=plan_data.estimated_cost,
        department=plan_data.department,
        status="DRAFT",
        created_by=current_user.id,
    )

    session.add(plan)
    await session.commit()
    await session.refresh(plan)

    return PlanResponse.model_validate(plan)


@router.get("", response_model=list[PlanResponse])
async def list_plans(
    status: str | None = None,
    asset_type: str | None = None,
    plan_type: str | None = None,
    priority: str | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> list[PlanResponse]:
    """List plans with filters."""
    query = select(AssetPlan)

    if status:
        query = query.where(AssetPlan.status == status)

    if plan_type:
        query = query.where(AssetPlan.plan_type == plan_type)

    if priority:
        query = query.where(AssetPlan.priority == priority)

    if asset_type:
        query = query.join(Asset).where(Asset.asset_type == asset_type.lower())

    query = query.order_by(AssetPlan.created_at.desc()).limit(limit).offset(offset)

    result = await session.execute(query)
    plans = result.scalars().all()

    return [PlanResponse.model_validate(p) for p in plans]


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(
    plan_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> PlanResponse:
    """Get plan by ID."""
    result = await session.execute(
        select(AssetPlan).where(AssetPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()

    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    return PlanResponse.model_validate(plan)


@router.post("/{plan_id}/submit")
async def submit_plan(
    plan_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_officer),
) -> dict[str, str]:
    """Submit plan for review (OFFICER only)."""
    result = await session.execute(
        select(AssetPlan).where(AssetPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()

    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    if plan.status != "DRAFT":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft plans can be submitted",
        )

    plan.status = "UNDER_REVIEW"
    plan.updated_at = datetime.now(UTC)

    await session.commit()

    return {"message": "Plan submitted for review"}


@router.post("/{plan_id}/approve")
async def approve_plan(
    plan_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_reviewer),
) -> dict[str, str]:
    """Approve plan (REVIEWER/ADMIN only)."""
    result = await session.execute(
        select(AssetPlan).where(AssetPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()

    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    if plan.status != "UNDER_REVIEW":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plan must be under review to approve",
        )

    plan.status = "APPROVED"
    plan.approved_by = current_user.id
    plan.updated_at = datetime.now(UTC)

    await session.commit()

    return {"message": "Plan approved"}


@router.post("/{plan_id}/reject")
async def reject_plan(
    plan_id: int,
    reason: str,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_reviewer),
) -> dict[str, str]:
    """Reject plan (REVIEWER/ADMIN only)."""
    result = await session.execute(
        select(AssetPlan).where(AssetPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()

    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    if plan.status != "UNDER_REVIEW":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Plan must be under review to reject",
        )

    plan.status = "REJECTED"
    plan.updated_at = datetime.now(UTC)

    await session.commit()

    return {"message": "Plan rejected"}


@router.post("/{plan_id}/revision")
async def request_revision(
    plan_id: int,
    comment: str,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_reviewer),
) -> dict[str, str]:
    """Request revision for plan (REVIEWER/ADMIN only)."""
    result = await session.execute(
        select(AssetPlan).where(AssetPlan.id == plan_id)
    )
    plan = result.scalar_one_or_none()

    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Plan not found",
        )

    plan.status = "REVISION_REQUIRED"
    plan.updated_at = datetime.now(UTC)

    await session.commit()

    return {"message": "Revision requested"}
