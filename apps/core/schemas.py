"""
Pydantic schemas for API validation
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from models import TaskPriority, TaskStatus

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
