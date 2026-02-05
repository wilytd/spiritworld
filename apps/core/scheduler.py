"""
Background task scheduler for Aegis Mesh
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from croniter import croniter
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from models import MaintenanceTask, TaskStatus, NotificationPreference
from notifications import notification_service
from config import config

logger = logging.getLogger(__name__)


class TaskScheduler:
    """APScheduler-based task scheduler for background jobs"""

    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self._is_running = False

    async def start(self):
        """Start the scheduler with configured jobs"""
        if self._is_running:
            return

        # Snooze checker - runs every 5 minutes
        self.scheduler.add_job(
            self._check_snooze_expirations,
            IntervalTrigger(seconds=config.scheduler.snooze_check_interval),
            id="snooze_checker",
            name="Check Snooze Expirations",
            replace_existing=True,
        )

        # Due notification checker - runs every hour
        self.scheduler.add_job(
            self._check_due_notifications,
            IntervalTrigger(seconds=config.scheduler.overdue_check_interval),
            id="due_checker",
            name="Check Due Tasks",
            replace_existing=True,
        )

        # Recurring task generator - runs daily at configured hour
        self.scheduler.add_job(
            self._generate_recurring_tasks,
            CronTrigger(hour=config.scheduler.recurring_generation_hour),
            id="recurring_generator",
            name="Generate Recurring Tasks",
            replace_existing=True,
        )

        self.scheduler.start()
        self._is_running = True
        logger.info("Task scheduler started")

    async def stop(self):
        """Stop the scheduler"""
        if self._is_running:
            self.scheduler.shutdown(wait=False)
            self._is_running = False
            logger.info("Task scheduler stopped")

    async def _check_snooze_expirations(self):
        """Reactivate tasks whose snooze period has expired"""
        logger.debug("Checking for expired snoozes...")

        async with AsyncSessionLocal() as db:
            try:
                now = datetime.utcnow()
                result = await db.execute(
                    select(MaintenanceTask).where(
                        and_(
                            MaintenanceTask.status == TaskStatus.SNOOZED,
                            MaintenanceTask.snooze_until != None,
                            MaintenanceTask.snooze_until <= now,
                        )
                    )
                )
                expired_tasks = result.scalars().all()

                for task in expired_tasks:
                    task.status = TaskStatus.PENDING
                    task.snooze_until = None
                    logger.info(f"Reactivated task {task.id}: {task.title}")

                if expired_tasks:
                    await db.commit()
                    logger.info(f"Reactivated {len(expired_tasks)} snoozed tasks")

            except Exception as e:
                logger.error(f"Error checking snooze expirations: {e}")
                await db.rollback()

    async def _check_due_notifications(self):
        """Send notifications for due and overdue tasks"""
        logger.debug("Checking for due/overdue tasks...")

        async with AsyncSessionLocal() as db:
            try:
                now = datetime.utcnow()
                warning_threshold = now + timedelta(hours=config.scheduler.due_warning_hours)

                # Find tasks due soon or overdue
                result = await db.execute(
                    select(MaintenanceTask).where(
                        and_(
                            MaintenanceTask.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS]),
                            MaintenanceTask.due_date != None,
                            MaintenanceTask.due_date <= warning_threshold,
                        )
                    )
                )
                due_tasks = result.scalars().all()

                # Get notification preferences
                pref_result = await db.execute(
                    select(NotificationPreference).where(NotificationPreference.enabled == True)
                )
                preferences = pref_result.scalars().all()

                if not preferences:
                    return

                for task in due_tasks:
                    # Skip if recently notified (within last hour)
                    if task.last_notification:
                        time_since_last = now - task.last_notification
                        if time_since_last.total_seconds() < 3600:
                            continue

                    # Determine notification type
                    notification_type = "overdue" if task.due_date < now else "due"

                    # Send notifications
                    results = await notification_service.send_task_notification(
                        task, preferences, notification_type
                    )

                    # Update notification tracking
                    if any(success for _, success, _ in results):
                        task.last_notification = now
                        task.notification_count = (task.notification_count or 0) + 1
                        logger.info(f"Sent {notification_type} notification for task {task.id}")

                await db.commit()

            except Exception as e:
                logger.error(f"Error checking due notifications: {e}")
                await db.rollback()

    async def _generate_recurring_tasks(self):
        """Generate task instances from recurring templates"""
        logger.debug("Generating recurring tasks...")

        async with AsyncSessionLocal() as db:
            try:
                # Find recurring task templates (tasks with recurrence_rule but no parent)
                result = await db.execute(
                    select(MaintenanceTask).where(
                        and_(
                            MaintenanceTask.recurrence_rule != None,
                            MaintenanceTask.recurrence_parent_id == None,
                        )
                    )
                )
                templates = result.scalars().all()

                now = datetime.utcnow()
                tomorrow = now + timedelta(days=1)

                for template in templates:
                    try:
                        # Parse cron expression and find next occurrence
                        cron = croniter(template.recurrence_rule, now)
                        next_due = cron.get_next(datetime)

                        # Only create if due within next 24 hours
                        if next_due > tomorrow:
                            continue

                        # Check if instance already exists for this due date
                        existing = await db.execute(
                            select(MaintenanceTask).where(
                                and_(
                                    MaintenanceTask.recurrence_parent_id == template.id,
                                    MaintenanceTask.due_date == next_due,
                                )
                            )
                        )
                        if existing.scalar_one_or_none():
                            continue

                        # Create new instance
                        new_task = MaintenanceTask(
                            title=template.title,
                            description=template.description,
                            category=template.category,
                            priority=template.priority,
                            status=TaskStatus.PENDING,
                            due_date=next_due,
                            mesh_notify=template.mesh_notify,
                            recurrence_parent_id=template.id,
                        )
                        db.add(new_task)
                        logger.info(f"Generated recurring task: {template.title} due {next_due}")

                    except Exception as e:
                        logger.error(f"Error processing recurring template {template.id}: {e}")

                await db.commit()

            except Exception as e:
                logger.error(f"Error generating recurring tasks: {e}")
                await db.rollback()


# Global scheduler instance
task_scheduler = TaskScheduler()
