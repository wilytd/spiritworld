"""
Multi-channel notification service for Aegis Mesh
"""

import asyncio
from datetime import datetime, time
from typing import Optional, List
import httpx
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import config, SMTPConfig, WebhookConfig
from models import NotificationPreference, TaskPriority, NotificationChannel, MaintenanceTask


class EmailSender:
    """Send notifications via SMTP email"""

    def __init__(self, smtp_config: SMTPConfig):
        self.config = smtp_config

    async def send(self, to_address: str, subject: str, body: str) -> tuple[bool, Optional[str]]:
        """Send an email notification"""
        if not self.config.is_configured:
            return False, "SMTP not configured"

        try:
            message = MIMEMultipart()
            message["From"] = self.config.from_address
            message["To"] = to_address
            message["Subject"] = subject
            message.attach(MIMEText(body, "plain"))

            await aiosmtplib.send(
                message,
                hostname=self.config.host,
                port=self.config.port,
                username=self.config.username or None,
                password=self.config.password or None,
                start_tls=self.config.use_tls,
            )
            return True, None
        except Exception as e:
            return False, str(e)


class WebhookSender:
    """Send notifications via webhooks (Slack, Discord, generic)"""

    def __init__(self, webhook_config: WebhookConfig):
        self.config = webhook_config

    async def send(
        self,
        message: str,
        webhook_url: Optional[str] = None,
        format_type: str = "generic"
    ) -> tuple[bool, Optional[str]]:
        """Send a webhook notification"""
        url = webhook_url or self._get_default_url(format_type)
        if not url:
            return False, f"No webhook URL configured for {format_type}"

        payload = self._format_payload(message, format_type)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, json=payload)
                if response.status_code in [200, 201, 204]:
                    return True, None
                return False, f"Webhook returned {response.status_code}"
        except Exception as e:
            return False, str(e)

    def _get_default_url(self, format_type: str) -> Optional[str]:
        if format_type == "slack":
            return self.config.slack_url
        elif format_type == "discord":
            return self.config.discord_url
        return self.config.generic_url

    def _format_payload(self, message: str, format_type: str) -> dict:
        if format_type == "slack":
            return {"text": message}
        elif format_type == "discord":
            return {"content": message}
        return {"text": message, "message": message}


class MeshSender:
    """Send notifications via Meshtastic mesh network"""

    def __init__(self, mesh_bridge_url: str):
        self.mesh_bridge_url = mesh_bridge_url

    async def send(self, message: str) -> tuple[bool, Optional[str]]:
        """Send a mesh notification"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.mesh_bridge_url}/send",
                    json={"message": message}
                )
                if response.status_code == 200:
                    return True, None
                return False, f"Mesh bridge returned {response.status_code}"
        except Exception as e:
            return False, str(e)


class NotificationService:
    """Orchestrates multi-channel notifications with preference filtering"""

    def __init__(self):
        self.email_sender = EmailSender(config.smtp)
        self.webhook_sender = WebhookSender(config.webhook)
        self.mesh_sender = MeshSender(config.mesh_bridge_url)

    async def send_task_notification(
        self,
        task: MaintenanceTask,
        preferences: List[NotificationPreference],
        notification_type: str = "due"
    ) -> List[tuple[NotificationChannel, bool, Optional[str]]]:
        """
        Send notifications for a task based on user preferences.
        Returns list of (channel, success, error) tuples.
        """
        results = []
        message = self._format_task_message(task, notification_type)

        for pref in preferences:
            if not self._should_notify(pref, task):
                continue

            success, error = await self._send_via_channel(pref, message, task)
            results.append((pref.channel, success, error))

        return results

    async def send_direct(
        self,
        channel: NotificationChannel,
        message: str,
        config_override: Optional[dict] = None
    ) -> tuple[bool, Optional[str]]:
        """Send a direct notification to a specific channel"""
        if channel == NotificationChannel.EMAIL:
            email = config_override.get("email") if config_override else None
            if not email:
                return False, "Email address required"
            return await self.email_sender.send(email, "Aegis Mesh Alert", message)

        elif channel == NotificationChannel.WEBHOOK:
            webhook_url = config_override.get("webhook_url") if config_override else None
            format_type = config_override.get("format", "generic") if config_override else "generic"
            return await self.webhook_sender.send(message, webhook_url, format_type)

        elif channel == NotificationChannel.MESH:
            return await self.mesh_sender.send(message)

        return False, f"Unknown channel: {channel}"

    async def test_channel(
        self,
        preference: NotificationPreference,
        message: str = "Test notification from Aegis Mesh"
    ) -> tuple[bool, Optional[str]]:
        """Test a notification channel"""
        return await self._send_via_channel(preference, message, task=None)

    def _should_notify(self, pref: NotificationPreference, task: MaintenanceTask) -> bool:
        """Check if notification should be sent based on preference settings"""
        if not pref.enabled:
            return False

        # Check priority threshold
        priority_order = [TaskPriority.LOW, TaskPriority.MEDIUM, TaskPriority.HIGH, TaskPriority.CRITICAL]
        if priority_order.index(task.priority) < priority_order.index(pref.min_priority):
            return False

        # Check category filter
        if pref.categories and task.category not in pref.categories:
            return False

        # Check quiet hours
        if pref.quiet_hours_start and pref.quiet_hours_end:
            if self._is_quiet_hours(pref.quiet_hours_start, pref.quiet_hours_end):
                return False

        return True

    def _is_quiet_hours(self, start: str, end: str) -> bool:
        """Check if current time is within quiet hours"""
        now = datetime.now().time()
        start_time = time.fromisoformat(start)
        end_time = time.fromisoformat(end)

        # Handle overnight quiet hours (e.g., 22:00 - 08:00)
        if start_time > end_time:
            return now >= start_time or now <= end_time
        return start_time <= now <= end_time

    async def _send_via_channel(
        self,
        pref: NotificationPreference,
        message: str,
        task: Optional[MaintenanceTask]
    ) -> tuple[bool, Optional[str]]:
        """Send notification via the preference's channel"""
        pref_config = pref.config or {}

        if pref.channel == NotificationChannel.EMAIL:
            email = pref_config.get("email")
            if not email:
                return False, "Email address not configured"
            subject = f"Aegis Mesh: {task.title}" if task else "Aegis Mesh Alert"
            return await self.email_sender.send(email, subject, message)

        elif pref.channel == NotificationChannel.WEBHOOK:
            webhook_url = pref_config.get("webhook_url")
            format_type = pref_config.get("format", "generic")
            return await self.webhook_sender.send(message, webhook_url, format_type)

        elif pref.channel == NotificationChannel.MESH:
            return await self.mesh_sender.send(message)

        return False, f"Unknown channel: {pref.channel}"

    def _format_task_message(self, task: MaintenanceTask, notification_type: str) -> str:
        """Format notification message for a task"""
        priority_emoji = {
            TaskPriority.LOW: "",
            TaskPriority.MEDIUM: "[MEDIUM]",
            TaskPriority.HIGH: "[HIGH]",
            TaskPriority.CRITICAL: "[CRITICAL]",
        }

        prefix = priority_emoji.get(task.priority, "")

        if notification_type == "due":
            return f"{prefix} Task due: {task.title} ({task.category})"
        elif notification_type == "overdue":
            return f"{prefix} OVERDUE: {task.title} ({task.category})"
        elif notification_type == "reminder":
            return f"{prefix} Reminder: {task.title} ({task.category})"
        else:
            return f"{prefix} {task.title} ({task.category})"


# Global notification service instance
notification_service = NotificationService()
