"""
Notification Scheduler

Background task to periodically reconcile date-based notifications.
Runs every NOTIFICATION_RECONCILE_SECONDS seconds.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import text

from app.db.session import SessionLocal
from app.services.notification_reconciler import reconcile_notifications

logger = logging.getLogger(__name__)


async def start_notification_scheduler(reconcile_interval: int = 60) -> asyncio.Task:
    """
    Start background notification reconciliation task.

    Args:
        reconcile_interval: Seconds between reconciliation runs (default: 60)

    Returns:
        asyncio.Task for the scheduler
    """
    async def scheduler_loop():
        logger.info(f"Starting notification reconciler (interval={reconcile_interval}s)")

        while True:
            try:
                await asyncio.sleep(reconcile_interval)

                async with SessionLocal() as session:
                    now = datetime.now(UTC)
                    counts = await reconcile_notifications(session, now)

                    total = sum(counts.values())
                    if total > 0:
                        logger.info(f"Reconciled notifications: {counts}")

            except Exception as e:
                logger.error(f"Error in notification reconciler: {e}", exc_info=True)
                # Continue on error, don't crash the scheduler
                await asyncio.sleep(5)  # Brief backoff before retry

    task = asyncio.create_task(scheduler_loop())
    return task


async def stop_notification_scheduler(task: asyncio.Task) -> None:
    """
    Stop background notification reconciliation task.

    Args:
        task: asyncio.Task returned by start_notification_scheduler
    """
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("Notification reconciler stopped")
