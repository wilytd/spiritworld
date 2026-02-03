"""
Aegis Mesh - Core Orchestrator Service
Central API for managing home lab infrastructure, maintenance tasks, and mesh communications.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from database import engine, get_db
from models import Base
from routers import tasks, status, alerts

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown: cleanup if needed
    await engine.dispose()

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
