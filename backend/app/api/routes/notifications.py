from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.operational import Notification
from app.schemas.notifications import NotificationCreate, NotificationResponse

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.post("", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification(
    notification_data: NotificationCreate,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> NotificationResponse:
    """Create a notification (internal use)."""
    notification = Notification(
        user_id=notification_data.user_id,
        notification_type=notification_data.notification_type,
        severity=notification_data.severity,
        title=notification_data.title,
        message=notification_data.message,
        asset_id=notification_data.asset_id,
        inspection_id=notification_data.inspection_id,
        maintenance_id=notification_data.maintenance_id,
        plan_id=notification_data.plan_id,
        link=notification_data.link,
        is_read=False,
    )

    session.add(notification)
    await session.commit()
    await session.refresh(notification)

    return NotificationResponse.model_validate(notification)


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    unread_only: bool = False,
    notification_type: str | None = None,
    severity: str | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> list[NotificationResponse]:
    """List notifications for current user."""
    if not current_user:
        return []

    query = select(Notification).where(Notification.user_id == current_user.id)

    if unread_only:
        query = query.where(Notification.is_read == False)

    if notification_type:
        query = query.where(Notification.notification_type == notification_type)

    if severity:
        query = query.where(Notification.severity == severity)

    query = query.order_by(Notification.created_at.desc()).limit(limit).offset(offset)

    result = await session.execute(query)
    notifications = result.scalars().all()

    return [NotificationResponse.model_validate(n) for n in notifications]


@router.get("/unread-count")
async def get_unread_count(
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, int]:
    """Get unread notification count for current user."""
    if not current_user:
        return {"count": 0}

    result = await session.execute(
        select(func.count())
        .where(Notification.user_id == current_user.id, Notification.is_read == False)
    )
    count = result.scalar() or 0

    return {"count": count}


@router.post("/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, str]:
    """Mark notification as read."""
    result = await session.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()

    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    notification.is_read = True
    notification.read_at = datetime.now(UTC)
    notification.updated_at = datetime.now(UTC)

    await session.commit()

    return {"message": "Notification marked as read"}


@router.post("/read-all")
async def mark_all_read(
    session: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
) -> dict[str, str]:
    """Mark all notifications as read."""
    if not current_user:
        return {"message": "No user"}

    result = await session.execute(
        select(Notification).where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,
        )
    )
    notifications = result.scalars().all()

    for notification in notifications:
        notification.is_read = True
        notification.read_at = datetime.now(UTC)
        notification.updated_at = datetime.now(UTC)

    await session.commit()

    return {"message": f"Marked {len(notifications)} notifications as read"}
