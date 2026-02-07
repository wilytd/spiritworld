"""
API endpoints for LLM service
"""

import logging
from typing import Optional, List
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import MaintenanceTask, TaskStatus
from .service import get_llm_service, LLMService

logger = logging.getLogger(__name__)
router = APIRouter()


# Request/Response schemas
class LLMStatusResponse(BaseModel):
    enabled: bool
    providers: dict
    priority: List[str]
    analysis_enabled: bool
    analysis_schedule: str


class ProviderCheckResponse(BaseModel):
    availability: dict


class TaskAnalysisRequest(BaseModel):
    task_id: int


class TaskAnalysisResponse(BaseModel):
    task_id: int
    analysis_type: str
    provider_used: str
    model: str
    data: dict


class BatchAnalysisRequest(BaseModel):
    task_ids: Optional[List[int]] = Field(
        None,
        description="Specific task IDs to analyze. If not provided, analyzes all pending tasks."
    )
    limit: int = Field(20, ge=1, le=100, description="Maximum tasks to analyze")


class BatchAnalysisResponse(BaseModel):
    analysis_type: str
    task_count: int
    provider_used: str
    model: str
    data: dict


class CompletionRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    temperature: float = Field(0.7, ge=0.0, le=1.0)
    max_tokens: Optional[int] = Field(None, ge=1, le=4096)


class CompletionResponse(BaseModel):
    content: str
    provider: str
    model: str
    usage: dict


def _get_service() -> LLMService:
    """Get LLM service or raise 503"""
    service = get_llm_service()
    if not service:
        raise HTTPException(status_code=503, detail="LLM service not initialized")
    return service


@router.get("/status", response_model=LLMStatusResponse)
async def get_llm_status():
    """Get LLM service and provider status"""
    service = _get_service()
    status = service.get_status()
    return LLMStatusResponse(
        enabled=status["enabled"],
        providers=status["providers"],
        priority=status["priority"],
        analysis_enabled=status["analysis_enabled"],
        analysis_schedule=status["analysis_schedule"],
    )


@router.post("/providers/check", response_model=ProviderCheckResponse)
async def check_providers():
    """Check availability of all LLM providers"""
    service = _get_service()
    availability = await service.check_availability()
    return ProviderCheckResponse(availability=availability)


@router.post("/analyze/task", response_model=TaskAnalysisResponse)
async def analyze_single_task(
    request: TaskAnalysisRequest,
    db: AsyncSession = Depends(get_db),
):
    """Analyze a single task and get recommendations"""
    service = _get_service()

    if not service.config.enabled:
        raise HTTPException(status_code=503, detail="LLM service is disabled")

    # Get task from database
    result = await db.execute(
        select(MaintenanceTask).where(MaintenanceTask.id == request.task_id)
    )
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # Convert to dict for analysis
    task_dict = {
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "category": task.category,
        "priority": task.priority.value if task.priority else None,
        "due_date": task.due_date.isoformat() if task.due_date else None,
        "status": task.status.value if task.status else None,
    }

    analysis = await service.analyze_task(task_dict)

    if not analysis:
        raise HTTPException(status_code=503, detail="No LLM providers available")

    return TaskAnalysisResponse(
        task_id=task.id,
        analysis_type=analysis["analysis_type"],
        provider_used=analysis["provider"],
        model=analysis["model"],
        data=analysis["data"],
    )


@router.post("/analyze/batch", response_model=BatchAnalysisResponse)
async def analyze_batch_tasks(
    request: BatchAnalysisRequest,
    db: AsyncSession = Depends(get_db),
):
    """Batch analyze pending tasks"""
    service = _get_service()

    if not service.config.enabled:
        raise HTTPException(status_code=503, detail="LLM service is disabled")

    # Build query
    query = select(MaintenanceTask)

    if request.task_ids:
        query = query.where(MaintenanceTask.id.in_(request.task_ids))
    else:
        # Default: pending and in_progress tasks
        query = query.where(
            MaintenanceTask.status.in_([TaskStatus.PENDING, TaskStatus.IN_PROGRESS])
        )

    query = query.limit(request.limit)

    result = await db.execute(query)
    tasks = result.scalars().all()

    if not tasks:
        raise HTTPException(status_code=404, detail="No tasks found for analysis")

    # Convert to dicts
    task_dicts = [
        {
            "id": t.id,
            "title": t.title,
            "description": t.description,
            "category": t.category,
            "priority": t.priority.value if t.priority else None,
            "due_date": t.due_date.isoformat() if t.due_date else None,
            "status": t.status.value if t.status else None,
        }
        for t in tasks
    ]

    analysis = await service.analyze_tasks_batch(task_dicts)

    if not analysis:
        raise HTTPException(status_code=503, detail="No LLM providers available")

    return BatchAnalysisResponse(
        analysis_type=analysis["analysis_type"],
        task_count=analysis["task_count"],
        provider_used=analysis["provider"],
        model=analysis["model"],
        data=analysis["data"],
    )


@router.post("/complete", response_model=CompletionResponse)
async def raw_completion(request: CompletionRequest):
    """Raw completion endpoint for general queries"""
    service = _get_service()

    if not service.config.enabled:
        raise HTTPException(status_code=503, detail="LLM service is disabled")

    from . import prompts

    response = await service.complete(
        prompt=request.prompt,
        system_prompt=request.system_prompt or prompts.RAW_COMPLETION_SYSTEM,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
    )

    if not response:
        raise HTTPException(status_code=503, detail="No LLM providers available")

    return CompletionResponse(
        content=response.content,
        provider=response.provider,
        model=response.model,
        usage=response.usage,
    )
