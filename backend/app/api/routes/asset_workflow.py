from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from app.api.deps import get_current_admin, get_current_officer, get_current_user, get_db
from app.models.entities import Asset
from app.models.operational import AssetAssignment, AssetReview
from app.schemas.asset_workflow import (
    AssetAssignmentCreate,
    AssetAssignmentResponse,
    AssetCreate,
    AssetReviewCreate,
    AssetReviewResponse,
    AssetResponse,
)

router = APIRouter(prefix="/assets", tags=["asset-workflow"])


@router.post("/new", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
async def create_asset(
    asset_data: AssetCreate,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_officer),
) -> AssetResponse:
    """Create a new asset proposal (OFFICER only)."""
    from sqlalchemy import func
    from geoalchemy2.shape import to_shape

    # Generate asset code
    asset_type_code = {
        "DAM": "AP_DAM",
        "BARRAGE": "AP_BAR",
        "BRIDGE": "AP_BR",
        "AIRPORT": "AP_AP",
        "TEMPLE": "AP_TP",
    }.get(asset_data.asset_type.upper(), "AP_AS")

    # Get next sequence number
    result = await session.execute(
        select(func.count())
        .where(Asset.asset_code.like(f"{asset_type_code}_%"))
    )
    count = result.scalar() or 0
    sequence = str(count + 1).zfill(5)
    asset_code = f"{asset_type_code}_{sequence}"

    # Create asset
    from geoalchemy2.elements import WKTElement

    geometry_wkt = f"POINT({asset_data.longitude} {asset_data.latitude})"
    geometry = WKTElement(geometry_wkt, srid=4326)

    asset = Asset(
        asset_code=asset_code,
        name=asset_data.official_name,
        asset_type=asset_data.asset_type.lower(),
        district=asset_data.district,
        owner=asset_data.owning_authority,
        status="ACTIVE",
        identity_status="PENDING_REVIEW",
        built_year=asset_data.construction_year,
        design_life_years=100,  # Default
        material=asset_data.material,
        representative_geometry=geometry,
        confidence_score=0.0,  # New submission
        is_estimated=True,
    )

    session.add(asset)
    await session.commit()
    await session.refresh(asset)

    return AssetResponse.model_validate(asset)


@router.post("/{asset_code}/submit")
async def submit_asset(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_officer),
) -> dict[str, str]:
    """Submit asset for review (OFFICER only)."""
    result = await session.execute(
        select(Asset).where(Asset.asset_code == asset_code)
    )
    asset = result.scalar_one_or_none()

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    if asset.identity_status == "PENDING_REVIEW":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset already submitted for review",
        )

    asset.identity_status = "PENDING_REVIEW"
    asset.updated_at = datetime.now(UTC)

    await session.commit()

    return {"message": "Asset submitted for review"}


@router.post("/{asset_code}/approve")
async def approve_asset(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_reviewer),
) -> dict[str, str]:
    """Approve asset (REVIEWER/ADMIN only)."""
    result = await session.execute(
        select(Asset).where(Asset.asset_code == asset_code)
    )
    asset = result.scalar_one_or_none()

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    if asset.identity_status not in {"PENDING_REVIEW", "NEEDS_VERIFICATION"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset cannot be approved in current state",
        )

    asset.identity_status = "IDENTITY_VERIFIED"
    asset.updated_at = datetime.now(UTC)

    await session.commit()

    return {"message": "Asset approved"}


@router.post("/{asset_code}/reject")
async def reject_asset(
    asset_code: str,
    reason: str,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_reviewer),
) -> dict[str, str]:
    """Reject asset (REVIEWER/ADMIN only)."""
    result = await session.execute(
        select(Asset).where(Asset.asset_code == asset_code)
    )
    asset = result.scalar_one_or_none()

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    if asset.identity_status != "PENDING_REVIEW":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset cannot be rejected in current state",
        )

    asset.identity_status = "REJECTED"
    asset.updated_at = datetime.now(UTC)

    await session.commit()

    return {"message": "Asset rejected"}


@router.post("/{asset_code}/review", response_model=AssetReviewResponse, status_code=status.HTTP_201_CREATED)
async def create_asset_review(
    asset_code: str,
    review_data: AssetReviewCreate,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_officer),
) -> AssetReviewResponse:
    """Create an asset review (OFFICER only)."""
    result = await session.execute(
        select(Asset).where(Asset.asset_code == asset_code)
    )
    asset = result.scalar_one_or_none()

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    review = AssetReview(
        asset_id=asset.id,
        reviewed_by=current_user.id,
        review_type=review_data.review_type,
        inspection_date=review_data.inspection_date,
        condition=review_data.condition,
        observation=review_data.observation,
        components_inspected=review_data.components_inspected,
        recommendation=review_data.recommendation,
        remarks=review_data.remarks,
        verification_status="PENDING_REVIEW",
    )

    session.add(review)
    await session.commit()
    await session.refresh(review)

    return AssetReviewResponse.model_validate(review)


@router.get("/{asset_code}/reviews", response_model=list[AssetReviewResponse])
async def get_asset_reviews(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> list[AssetReviewResponse]:
    """Get all reviews for an asset."""
    result = await session.execute(
        select(Asset).where(Asset.asset_code == asset_code)
    )
    asset = result.scalar_one_or_none()

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    result = await session.execute(
        select(AssetReview)
        .where(AssetReview.asset_id == asset.id)
        .order_by(AssetReview.created_at.desc())
    )
    reviews = result.scalars().all()

    return [AssetReviewResponse.model_validate(r) for r in reviews]


@router.post("/{asset_code}/assign", response_model=AssetAssignmentResponse, status_code=status.HTTP_201_CREATED)
async def assign_asset(
    asset_code: str,
    assignment_data: AssetAssignmentCreate,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_admin),
) -> AssetAssignmentResponse:
    """Assign asset to a user (ADMIN only)."""
    result = await session.execute(
        select(Asset).where(Asset.asset_code == asset_code)
    )
    asset = result.scalar_one_or_none()

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    assignment = AssetAssignment(
        asset_id=asset.id,
        user_id=assignment_data.assigned_to,
        assignment_type=assignment_data.assignment_type,
        assigned_by=current_user.id,
        assigned_at=datetime.now(UTC),
    )

    session.add(assignment)
    await session.commit()
    await session.refresh(assignment)

    return AssetAssignmentResponse.model_validate(assignment)


@router.get("/{asset_code}/assignments", response_model=list[AssetAssignmentResponse])
async def get_asset_assignments(
    asset_code: str,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> list[AssetAssignmentResponse]:
    """Get all assignments for an asset."""
    result = await session.execute(
        select(Asset).where(Asset.asset_code == asset_code)
    )
    asset = result.scalar_one_or_none()

    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found",
        )

    result = await session.execute(
        select(AssetAssignment)
        .where(AssetAssignment.asset_id == asset.id, AssetAssignment.is_active == True)
        .order_by(AssetAssignment.assigned_at.desc())
    )
    assignments = result.scalars().all()

    return [AssetAssignmentResponse.model_validate(a) for a in assignments]
