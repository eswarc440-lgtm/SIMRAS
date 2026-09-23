"""
Notification Reconciler

Periodically reconciles date-based notification events (due, overdue)
that should exist independent of user actions.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Asset
from app.models.operational import (
    Inspection,
    Maintenance,
    Notification,
    User,
)
from app.services.notification_service import (
    NotificationType,
    NotificationSeverity,
    create_notification,
    notify_user,
)


async def reconcile_notifications(
    session: AsyncSession,
    now: datetime | None = None,
) -> dict[str, int]:
    """
    Reconcile all date-based notifications.

    Checks for inspections and maintenance that are due or overdue,
    creating notifications if they don't already exist.

    Args:
        session: Database session
        now: Current time (default: UTC now)

    Returns:
        Dictionary with counts: {
            "inspection_due_created": N,
            "inspection_overdue_created": N,
            "maintenance_due_created": N,
            "maintenance_overdue_created": N,
        }
    """
    if now is None:
        now = datetime.now(UTC)

    counts = {
        "inspection_due_created": 0,
        "inspection_overdue_created": 0,
        "maintenance_overdue_created": 0,
        "maintenance_scheduled_created": 0,
    }

    # Reconcile inspection due notifications
    counts["inspection_due_created"] += await reconcile_inspection_due(session, now)

    # Reconcile inspection overdue notifications
    counts["inspection_overdue_created"] += await reconcile_inspection_overdue(session, now)

    # Reconcile maintenance overdue notifications
    counts["maintenance_overdue_created"] += await reconcile_maintenance_overdue(session, now)

    # Reconcile maintenance scheduled notifications
    counts["maintenance_scheduled_created"] += await reconcile_maintenance_scheduled(session, now)

    return counts


async def reconcile_inspection_due(
    session: AsyncSession,
    now: datetime,
) -> int:
    """
    Create inspection due notifications for inspections due within 7 days.

    Args:
        session: Database session
        now: Current time

    Returns:
        Number of notifications created
    """
    due_before = now + timedelta(days=7)
    due_after = now

    result = await session.execute(
        select(Inspection).where(
            Inspection.status.in_(["SCHEDULED", "IN_PROGRESS"]),
            Inspection.due_date >= due_after,
            Inspection.due_date <= due_before,
            Inspection.assigned_officer.isnot(None),
        )
    )
    inspections = result.scalars().all()

    created = 0
    for inspection in inspections:
        # Check if already notified
        dedupe_key = f"inspection_due:{inspection.id}:{inspection.due_date.date()}"

        result = await session.execute(
            select(Notification).where(
                Notification.inspection_id == inspection.id,
                Notification.notification_type == NotificationType.INSPECTION_DUE,
                Notification.user_id == inspection.assigned_officer,
            )
        )

        if result.scalar_one_or_none():
            continue  # Already notified

        notification = await notify_user(
            session,
            user_id=inspection.assigned_officer,
            notification_type=NotificationType.INSPECTION_DUE,
            severity=NotificationSeverity.MEDIUM,
            title=f"Inspection Due: {inspection.asset_code}",
            message=f"Inspection scheduled for {inspection.due_date.strftime('%Y-%m-%d')}",
            inspection_id=inspection.id,
            asset_id=inspection.asset_id,
            link=f"/inspections/{inspection.id}/view",
        )

        if notification:
            created += 1

    return created


async def reconcile_inspection_overdue(
    session: AsyncSession,
    now: datetime,
) -> int:
    """
    Create inspection overdue notifications for inspections past due.

    Args:
        session: Database session
        now: Current time

    Returns:
        Number of notifications created
    """
    result = await session.execute(
        select(Inspection).where(
            Inspection.status.in_(["SCHEDULED", "IN_PROGRESS"]),
            Inspection.due_date < now,
            Inspection.assigned_officer.isnot(None),
        )
    )
    inspections = result.scalars().all()

    created = 0
    for inspection in inspections:
        # Check if already notified (dedupe by inspection and overdue status)
        result = await session.execute(
            select(Notification).where(
                Notification.inspection_id == inspection.id,
                Notification.notification_type == NotificationType.INSPECTION_OVERDUE,
                Notification.user_id == inspection.assigned_officer,
            )
        )

        if result.scalar_one_or_none():
            continue  # Already notified

        days_overdue = (now.date() - inspection.due_date.date()).days

        notification = await notify_user(
            session,
            user_id=inspection.assigned_officer,
            notification_type=NotificationType.INSPECTION_OVERDUE,
            severity=NotificationSeverity.HIGH,
            title=f"Inspection Overdue: {inspection.asset_code}",
            message=f"Inspection was due {days_overdue} days ago ({inspection.due_date.strftime('%Y-%m-%d')})",
            inspection_id=inspection.id,
            asset_id=inspection.asset_id,
            link=f"/inspections/{inspection.id}/view",
        )

        if notification:
            created += 1

    return created


async def reconcile_maintenance_overdue(
    session: AsyncSession,
    now: datetime,
) -> int:
    """
    Create maintenance overdue notifications for maintenance past due.

    Args:
        session: Database session
        now: Current time

    Returns:
        Number of notifications created
    """
    result = await session.execute(
        select(Maintenance).where(
            Maintenance.status.in_(["SCHEDULED", "IN_PROGRESS"]),
            Maintenance.due_date < now,
        )
    )
    maintenance_records = result.scalars().all()

    created = 0
    for maintenance in maintenance_records:
        # Check if already notified
        result = await session.execute(
            select(Notification).where(
                Notification.maintenance_id == maintenance.id,
                Notification.notification_type == NotificationType.MAINTENANCE_OVERDUE,
            )
        )

        if result.scalar_one_or_none():
            continue  # Already notified

        days_overdue = (now.date() - maintenance.due_date.date()).days

        # Notify created_by user
        notification = await notify_user(
            session,
            user_id=maintenance.created_by,
            notification_type=NotificationType.MAINTENANCE_OVERDUE,
            severity=NotificationSeverity.HIGH,
            title=f"Maintenance Overdue: {maintenance.asset_code}",
            message=f"Maintenance was due {days_overdue} days ago ({maintenance.due_date.strftime('%Y-%m-%d')})",
            maintenance_id=maintenance.id,
            asset_id=maintenance.asset_id,
            link=f"/maintenance/{maintenance.id}/view",
        )

        if notification:
            created += 1

    return created


async def reconcile_maintenance_scheduled(
    session: AsyncSession,
    now: datetime,
) -> int:
    """
    Create maintenance scheduled notifications for upcoming maintenance.

    Args:
        session: Database session
        now: Current time

    Returns:
        Number of notifications created
    """
    upcoming_before = now + timedelta(days=7)
    upcoming_after = now

    result = await session.execute(
        select(Maintenance).where(
            Maintenance.status == "SCHEDULED",
            Maintenance.start_date >= upcoming_after,
            Maintenance.start_date <= upcoming_before,
        )
    )
    maintenance_records = result.scalars().all()

    created = 0
    for maintenance in maintenance_records:
        # Check if already notified
        result = await session.execute(
            select(Notification).where(
                Notification.maintenance_id == maintenance.id,
                Notification.notification_type == NotificationType.MAINTENANCE_SCHEDULED,
                Notification.user_id == maintenance.created_by,
            )
        )

        if result.scalar_one_or_none():
            continue  # Already notified

        notification = await notify_user(
            session,
            user_id=maintenance.created_by,
            notification_type=NotificationType.MAINTENANCE_SCHEDULED,
            severity=NotificationSeverity.INFO,
            title=f"Maintenance Scheduled: {maintenance.asset_code}",
            message=f"Maintenance scheduled for {maintenance.start_date.strftime('%Y-%m-%d')}",
            maintenance_id=maintenance.id,
            asset_id=maintenance.asset_id,
            link=f"/maintenance/{maintenance.id}/view",
        )

        if notification:
            created += 1

    return created
