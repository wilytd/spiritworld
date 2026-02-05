"""
Pydantic schemas for API validation
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Any
from models import TaskPriority, TaskStatus, NotificationChannel

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: str
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: Optional[datetime] = None
    mesh_notify: bool = False

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    priority: Optional[TaskPriority] = None
    status: Optional[TaskStatus] = None
    due_date: Optional[datetime] = None
    mesh_notify: Optional[bool] = None

class TaskResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    category: str
    priority: TaskPriority
    status: TaskStatus
    due_date: Optional[datetime]
    mesh_notify: bool
    created_at: datetime
    updated_at: Optional[datetime]
    completed_at: Optional[datetime]
    recurrence_rule: Optional[str] = None
    recurrence_parent_id: Optional[int] = None
    snooze_until: Optional[datetime] = None
    last_notification: Optional[datetime] = None
    notification_count: int = 0

    class Config:
        from_attributes = True

class AlertCreate(BaseModel):
    message: str
    channel: str = "mesh"

class AlertResponse(BaseModel):
    id: int
    message: str
    channel: str
    sent_at: datetime
    success: bool
    error_message: Optional[str]

    class Config:
        from_attributes = True

class StatusResponse(BaseModel):
    service: str
    version: str
    database: str
    mesh_bridge: str
    uptime_seconds: float


# Snooze schemas
class SnoozeRequest(BaseModel):
    duration_minutes: Optional[int] = Field(None, ge=1, le=43200)  # max 30 days
    until: Optional[datetime] = None


# Recurring task schemas
class RecurringTaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    category: str
    priority: TaskPriority = TaskPriority.MEDIUM
    mesh_notify: bool = False
    recurrence_rule: str = Field(..., description="Cron expression, e.g., '0 9 * * 1' for Monday 9am")


# Notification preference schemas
class NotificationPreferenceCreate(BaseModel):
    channel: NotificationChannel
    enabled: bool = True
    config: Optional[dict] = None
    min_priority: TaskPriority = TaskPriority.LOW
    categories: Optional[List[str]] = None
    quiet_hours_start: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    quiet_hours_end: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")


class NotificationPreferenceUpdate(BaseModel):
    channel: Optional[NotificationChannel] = None
    enabled: Optional[bool] = None
    config: Optional[dict] = None
    min_priority: Optional[TaskPriority] = None
    categories: Optional[List[str]] = None
    quiet_hours_start: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    quiet_hours_end: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")


class NotificationPreferenceResponse(BaseModel):
    id: int
    channel: NotificationChannel
    enabled: bool
    config: Optional[dict]
    min_priority: TaskPriority
    categories: Optional[List[str]]
    quiet_hours_start: Optional[str]
    quiet_hours_end: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TestNotificationRequest(BaseModel):
    message: str = "Test notification from Aegis Mesh"


# LLM Analysis schemas
class LLMAnalysisLogResponse(BaseModel):
    id: int
    task_id: Optional[int]
    analysis_type: str
    provider_used: str
    model_used: str
    response_json: Optional[dict]
    created_at: datetime

    class Config:
        from_attributes = True


# Plugin schemas
class PluginStateResponse(BaseModel):
    id: int
    plugin_name: str
    enabled: bool
    config_json: Optional[dict]
    state_json: Optional[dict]
    last_error: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True
