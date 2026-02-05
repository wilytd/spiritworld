"""
Configuration settings for Aegis Mesh Core
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SMTPConfig:
    """SMTP configuration for email notifications"""
    host: str = ""
    port: int = 587
    username: str = ""
    password: str = ""
    from_address: str = ""
    use_tls: bool = True

    @classmethod
    def from_env(cls) -> "SMTPConfig":
        return cls(
            host=os.getenv("SMTP_HOST", ""),
            port=int(os.getenv("SMTP_PORT", "587")),
            username=os.getenv("SMTP_USERNAME", ""),
            password=os.getenv("SMTP_PASSWORD", ""),
            from_address=os.getenv("SMTP_FROM_ADDRESS", ""),
            use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.host and self.from_address)


@dataclass
class WebhookConfig:
    """Webhook configuration for Slack/Discord notifications"""
    slack_url: str = ""
    discord_url: str = ""
    generic_url: str = ""

    @classmethod
    def from_env(cls) -> "WebhookConfig":
        return cls(
            slack_url=os.getenv("SLACK_WEBHOOK_URL", ""),
            discord_url=os.getenv("DISCORD_WEBHOOK_URL", ""),
            generic_url=os.getenv("WEBHOOK_URL", ""),
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.slack_url or self.discord_url or self.generic_url)


@dataclass
class SchedulerConfig:
    """Scheduler configuration for background jobs"""
    due_warning_hours: int = 24
    overdue_check_interval: int = 3600  # seconds
    snooze_check_interval: int = 300  # 5 minutes
    recurring_generation_hour: int = 0  # midnight

    @classmethod
    def from_env(cls) -> "SchedulerConfig":
        return cls(
            due_warning_hours=int(os.getenv("SCHEDULER_DUE_WARNING_HOURS", "24")),
            overdue_check_interval=int(os.getenv("SCHEDULER_OVERDUE_CHECK_INTERVAL", "3600")),
            snooze_check_interval=int(os.getenv("SCHEDULER_SNOOZE_CHECK_INTERVAL", "300")),
            recurring_generation_hour=int(os.getenv("SCHEDULER_RECURRING_HOUR", "0")),
        )


@dataclass
class AppConfig:
    """Main application configuration"""
    smtp: SMTPConfig = field(default_factory=SMTPConfig)
    webhook: WebhookConfig = field(default_factory=WebhookConfig)
    scheduler: SchedulerConfig = field(default_factory=SchedulerConfig)
    mesh_bridge_url: str = "http://mesh-bridge:8001"

    @classmethod
    def from_env(cls) -> "AppConfig":
        return cls(
            smtp=SMTPConfig.from_env(),
            webhook=WebhookConfig.from_env(),
            scheduler=SchedulerConfig.from_env(),
            mesh_bridge_url=os.getenv("MESH_BRIDGE_URL", "http://mesh-bridge:8001"),
        )


# Global config instance
config = AppConfig.from_env()
