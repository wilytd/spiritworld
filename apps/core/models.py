"""
Database models for Aegis Mesh Core
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base
import enum


class TaskPriority(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SNOOZED = "snoozed"


class NotificationChannel(str, enum.Enum):
    MESH = "mesh"
    EMAIL = "email"
    WEBHOOK = "webhook"


class MaintenanceTask(Base):
    __tablename__ = "maintenance_tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(String(1000))
    category = Column(String(100), nullable=False)
    priority = Column(Enum(TaskPriority), default=TaskPriority.MEDIUM)
    status = Column(Enum(TaskStatus), default=TaskStatus.PENDING)
    due_date = Column(DateTime)
    mesh_notify = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
    completed_at = Column(DateTime)

    # Recurring task fields
    recurrence_rule = Column(String(100))  # Cron expression: "0 9 * * 1"
    recurrence_parent_id = Column(Integer, ForeignKey("maintenance_tasks.id"))

    # Snooze with duration
    snooze_until = Column(DateTime)

    # Notification tracking
    last_notification = Column(DateTime)
    notification_count = Column(Integer, default=0)

    # Relationships
    recurrence_parent = relationship("MaintenanceTask", remote_side=[id], backref="recurring_instances")

class AlertLog(Base):
    __tablename__ = "alert_logs"

    id = Column(Integer, primary_key=True, index=True)
    message = Column(String(500), nullable=False)
    channel = Column(String(50), nullable=False)  # mesh, email, webhook
    sent_at = Column(DateTime, server_default=func.now())
    success = Column(Boolean, default=True)
    error_message = Column(String(500))


class NotificationPreference(Base):
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    channel = Column(Enum(NotificationChannel), nullable=False)
    enabled = Column(Boolean, default=True)
    config = Column(JSON)  # {"email": "user@example.com"} or {"webhook_url": "...", "format": "slack"}
    min_priority = Column(Enum(TaskPriority), default=TaskPriority.LOW)  # Only notify for this priority or higher
    categories = Column(JSON)  # Filter by category, null = all categories
    quiet_hours_start = Column(String(5))  # "22:00"
    quiet_hours_end = Column(String(5))  # "08:00"
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())


class LLMAnalysisLog(Base):
    """Log of LLM analysis operations"""
    __tablename__ = "llm_analysis_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("maintenance_tasks.id"), nullable=True)
    analysis_type = Column(String(50))  # "single", "batch"
    provider_used = Column(String(50))
    model_used = Column(String(100))
    response_json = Column(JSON)
    created_at = Column(DateTime, server_default=func.now())

    # Relationship
    task = relationship("MaintenanceTask", backref="llm_analyses")


class PluginState(Base):
    """Persistent state for plugins"""
    __tablename__ = "plugin_states"

    id = Column(Integer, primary_key=True, index=True)
    plugin_name = Column(String(100), unique=True, nullable=False)
    enabled = Column(Boolean, default=True)
    config_json = Column(JSON)  # Plugin-specific configuration
    state_json = Column(JSON)  # Plugin runtime state
    last_error = Column(String(500))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
