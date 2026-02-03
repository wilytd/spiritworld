"""
Maintenance Tasks API Router
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import List

from database import get_db
from models import MaintenanceTask, TaskStatus
from schemas import TaskCreate, TaskUpdate, TaskResponse

router = APIRouter()

@router.get("/", response_model=List[TaskResponse])
async def list_tasks(
    status: TaskStatus = None,
    category: str = None,
    db: AsyncSession = Depends(get_db)
):
    """List all maintenance tasks with optional filtering"""
    query = select(MaintenanceTask)

    if status:
        query = query.where(MaintenanceTask.status == status)
    if category:
        query = query.where(MaintenanceTask.category == category)

    query = query.order_by(MaintenanceTask.due_date)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/", response_model=TaskResponse)
async def create_task(task: TaskCreate, db: AsyncSession = Depends(get_db)):
    """Create a new maintenance task"""
    db_task = MaintenanceTask(**task.model_dump())
    db.add(db_task)
    await db.commit()
    await db.refresh(db_task)
    return db_task

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Get a specific task by ID"""
    result = await db.execute(
        select(MaintenanceTask).where(MaintenanceTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: int,
    task_update: TaskUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a maintenance task"""
    result = await db.execute(
        select(MaintenanceTask).where(MaintenanceTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = task_update.model_dump(exclude_unset=True)

    # Set completed_at if status changed to completed
    if update_data.get("status") == TaskStatus.COMPLETED:
        update_data["completed_at"] = datetime.utcnow()

    for field, value in update_data.items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)
    return task

@router.delete("/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a maintenance task"""
    result = await db.execute(
        select(MaintenanceTask).where(MaintenanceTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    await db.delete(task)
    await db.commit()
    return {"deleted": True}

@router.post("/{task_id}/snooze", response_model=TaskResponse)
async def snooze_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Snooze a task"""
    result = await db.execute(
        select(MaintenanceTask).where(MaintenanceTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = TaskStatus.SNOOZED
    await db.commit()
    await db.refresh(task)
    return task

@router.post("/{task_id}/complete", response_model=TaskResponse)
async def complete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """Mark a task as completed"""
    result = await db.execute(
        select(MaintenanceTask).where(MaintenanceTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = TaskStatus.COMPLETED
    task.completed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(task)
    return task
