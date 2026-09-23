"""
Notification Service

Provides unified interface for creating notifications across all workflows.
Handles recipient routing, deduplication, and transactional integrity.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from enum import Enum

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entities import Asset
from app.models.operational import Notification, User


class NotificationType(str, Enum):
    """Notification types for all workflows."""
    # Asset workflow
    ASSET_SUBMITTED = "ASSET_SUBMITTED"
    ASSET_APPROVED = "ASSET_APPROVED"
    ASSET_REJECTED = "ASSET_REJECTED"
    ASSET_REVISION_REQUIRED = "ASSET_REVISION_REQUIRED"

    # Inspection workflow
    INSPECTION_DUE = "INSPECTION_DUE"
    INSPECTION_OVERDUE = "INSPECTION_OVERDUE"
    INSPECTION_SUBMITTED = "INSPECTION_SUBMITTED"
    INSPECTION_APPROVED = "INSPECTION_APPROVED"
    INSPECTION_REVISION_REQUIRED = "INSPECTION_REVISION_REQUIRED"

    # Maintenance workflow
    MAINTENANCE_APPROVED = "MAINTENANCE_APPROVED"
    MAINTENANCE_SCHEDULED = "MAINTENANCE_SCHEDULED"
    MAINTENANCE_OVERDUE = "MAINTENANCE_OVERDUE"
    MAINTENANCE_COMPLETED = "MAINTENANCE_COMPLETED"
    MAINTENANCE_VERIFIED = "MAINTENANCE_VERIFIED"

    # Plan workflow
    PLAN_SUBMITTED = "PLAN_SUBMITTED"
    PLAN_APPROVED = "PLAN_APPROVED"
    PLAN_REJECTED = "PLAN_REJECTED"
    PLAN_REVISION_REQUIRED = "PLAN_REVISION_REQUIRED"

    # Risk & Assessment
    RISK_CHANGE = "RISK_CHANGE"
    HIGH_RISK = "HIGH_RISK"

    # Evidence
    EVIDENCE_ADDED = "EVIDENCE_ADDED"
    EVIDENCE_CONFLICT = "EVIDENCE_CONFLICT"

    # System
    SYSTEM = "SYSTEM"


class NotificationSeverity(str, Enum):
    """Notification severity levels."""
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


async def create_notification(
    session: AsyncSession,
    *,
    user_id: int,
    notification_type: str | NotificationType,
    severity: str | NotificationSeverity = NotificationSeverity.INFO,
    title: str,
    message: str,
    asset_id: int | None = None,
    inspection_id: int | None = None,
    maintenance_id: int | None = None,
    plan_id: int | None = None,
    link: str | None = None,
    dedupe_key: str | None = None,
) -> Notification | None:
    """
    Create a notification for a user.

    Args:
        session: Database session
        user_id: Recipient user ID
        notification_type: Type of notification
        severity: Severity level
        title: Notification title
        message: Notification message
        asset_id: Related asset ID (optional)
        inspection_id: Related inspection ID (optional)
        maintenance_id: Related maintenance ID (optional)
        plan_id: Related plan ID (optional)
        link: URL to open when clicked (optional)
        dedupe_key: Key for deduplication (optional)

    Returns:
        Created notification or None if deduped
    """
    # Validate recipient exists and is active
    result = await session.execute(
        select(User).where(
            User.id == user_id,
            User.is_active == True,
        )
    )
    recipient = result.scalar_one_or_none()

    if recipient is None:
        return None

    # Check for duplicate if dedupe_key provided
    if dedupe_key:
        result = await session.execute(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.notification_type == str(notification_type),
            )
        )
        existing = result.scalar_one_or_none()

        if existing and hasattr(existing, '_dedupe_key'):
            if existing._dedupe_key == dedupe_key:
                # Duplicate detected, skip
                return None

    notification = Notification(
        user_id=user_id,
        notification_type=str(notification_type),
        severity=str(severity),
        title=title,
        message=message,
        asset_id=asset_id,
        inspection_id=inspection_id,
        maintenance_id=maintenance_id,
        plan_id=plan_id,
        link=link,
        is_read=False,
        read_at=None,
    )

    if dedupe_key:
        notification._dedupe_key = dedupe_key

    session.add(notification)
    # Don't commit here - caller controls transaction
    return notification


async def notify_asset_officers(
    session: AsyncSession,
    *,
    asset_id: int,
    notification_type: str,
    severity: str = "INFO",
    title: str,
    message: str,
    exclude_user_id: int | None = None,
    link: str | None = None,
) -> int:
    """
    Notify all officers assigned to an asset.

    Args:
        session: Database session
        asset_id: Asset ID
        notification_type: Type of notification
        severity: Severity level
        title: Notification title
        message: Notification message
        exclude_user_id: User ID to exclude (e.g., the submitter)
        link: URL to open when clicked

    Returns:
        Number of notifications created
    """
    from app.models.operational import AssetAssignment

    result = await session.execute(
        select(AssetAssignment.user_id)
        .where(
            AssetAssignment.asset_id == asset_id,
            AssetAssignment.is_active == True,
        )
        .distinct()
    )
    user_ids = result.scalars().all()

    count = 0
    for user_id in user_ids:
        if exclude_user_id and user_id == exclude_user_id:
            continue

        notification = await create_notification(
            session,
            user_id=user_id,
            notification_type=notification_type,
            severity=severity,
            title=title,
            message=message,
            asset_id=asset_id,
            link=link or f"/assets/{asset_id}/workspace",
        )

        if notification:
            count += 1

    return count


async def notify_reviewers(
    session: AsyncSession,
    *,
    notification_type: str,
    severity: str = "INFO",
    title: str,
    message: str,
    asset_id: int | None = None,
    inspection_id: int | None = None,
    maintenance_id: int | None = None,
    plan_id: int | None = None,
    link: str | None = None,
) -> int:
    """
    Notify all active reviewers.

    Args:
        session: Database session
        notification_type: Type of notification
        severity: Severity level
        title: Notification title
        message: Notification message
        asset_id: Related asset ID (optional)
        inspection_id: Related inspection ID (optional)
        maintenance_id: Related maintenance ID (optional)
        plan_id: Related plan ID (optional)
        link: URL to open when clicked

    Returns:
        Number of notifications created
    """
    result = await session.execute(
        select(User.id)
        .where(
            User.role.in_(["REVIEWER", "ADMIN"]),
            User.is_active == True,
        )
        .distinct()
    )
    reviewer_ids = result.scalars().all()

    count = 0
    for user_id in reviewer_ids:
        notification = await create_notification(
            session,
            user_id=user_id,
            notification_type=notification_type,
            severity=severity,
            title=title,
            message=message,
            asset_id=asset_id,
            inspection_id=inspection_id,
            maintenance_id=maintenance_id,
            plan_id=plan_id,
            link=link,
        )

        if notification:
            count += 1

    return count


async def notify_admins(
    session: AsyncSession,
    *,
    notification_type: str,
    severity: str = "INFO",
    title: str,
    message: str,
    asset_id: int | None = None,
    inspection_id: int | None = None,
    maintenance_id: int | None = None,
    plan_id: int | None = None,
    link: str | None = None,
) -> int:
    """
    Notify all active admins.

    Args:
        session: Database session
        notification_type: Type of notification
        severity: Severity level
        title: Notification title
        message: Notification message
        asset_id: Related asset ID (optional)
        inspection_id: Related inspection ID (optional)
        maintenance_id: Related maintenance ID (optional)
        plan_id: Related plan ID (optional)
        link: URL to open when clicked

    Returns:
        Number of notifications created
    """
    result = await session.execute(
        select(User.id).where(
            User.role == "ADMIN",
            User.is_active == True,
        )
    )
    admin_ids = result.scalars().all()

    count = 0
    for user_id in admin_ids:
        notification = await create_notification(
            session,
            user_id=user_id,
            notification_type=notification_type,
            severity=severity,
            title=title,
            message=message,
            asset_id=asset_id,
            inspection_id=inspection_id,
            maintenance_id=maintenance_id,
            plan_id=plan_id,
            link=link,
        )

        if notification:
            count += 1

    return count


async def notify_user(
    session: AsyncSession,
    *,
    user_id: int,
    notification_type: str,
    severity: str = "INFO",
    title: str,
    message: str,
    asset_id: int | None = None,
    inspection_id: int | None = None,
    maintenance_id: int | None = None,
    plan_id: int | None = None,
    link: str | None = None,
) -> Notification | None:
    """
    Notify a specific user.

    Args:
        session: Database session
        user_id: Recipient user ID
        notification_type: Type of notification
        severity: Severity level
        title: Notification title
        message: Notification message
        asset_id: Related asset ID (optional)
        inspection_id: Related inspection ID (optional)
        maintenance_id: Related maintenance ID (optional)
        plan_id: Related plan ID (optional)
        link: URL to open when clicked

    Returns:
        Created notification or None if user inactive
    """
    return await create_notification(
        session,
        user_id=user_id,
        notification_type=notification_type,
        severity=severity,
        title=title,
        message=message,
        asset_id=asset_id,
        inspection_id=inspection_id,
        maintenance_id=maintenance_id,
        plan_id=plan_id,
        link=link,
    )
