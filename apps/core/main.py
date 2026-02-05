"""
Aegis Mesh - Core Orchestrator Service
Central API for managing home lab infrastructure, maintenance tasks, and mesh communications.
"""

import logging
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from database import engine, get_db
from models import Base
from routers import tasks, status, alerts, notifications
from scheduler import task_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Start the background scheduler
    await task_scheduler.start()
    logger.info("Aegis Mesh Core started")

    yield

    # Shutdown: stop scheduler and cleanup
    await task_scheduler.stop()
    await engine.dispose()
    logger.info("Aegis Mesh Core stopped")

app = FastAPI(
    title="Aegis Mesh Core",
    description="Unified management layer for hybrid home lab infrastructure",
    version="0.1.0",
    lifespan=lifespan
)

# CORS for dashboard communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://dashboard:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tasks.router, prefix="/api/tasks", tags=["tasks"])
app.include_router(status.router, prefix="/api/status", tags=["status"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["alerts"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["notifications"])

@app.get("/")
async def root():
    return {
        "service": "Aegis Mesh Core",
        "version": "0.1.0",
        "status": "operational"
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
