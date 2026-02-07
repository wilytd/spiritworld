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
from routers import plugins as plugins_router
from scheduler import task_scheduler
from config import config
from plugins import PluginManager
from llm import LLMConfig
from llm.service import init_llm_service, get_llm_service
from llm.router import router as llm_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Global plugin manager instance
plugin_manager: PluginManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global plugin_manager

    # Startup: Create database tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Initialize LLM service
    llm_config = LLMConfig.from_env()
    llm_service = init_llm_service(llm_config)
    if llm_config.enabled:
        await llm_service.check_availability()
        logger.info("LLM service initialized")

    # Initialize plugin system
    if config.plugins.enabled:
        plugin_manager = PluginManager(
            plugins_dir=config.plugins.plugins_dir,
            auto_discover=config.plugins.auto_discover,
            enabled_list=config.plugins.enabled_list or None,
            disabled_list=config.plugins.disabled_list or None,
            get_db_session=get_db,
        )
        plugins_router.set_plugin_manager(plugin_manager)

        # Discover and load plugins
        await plugin_manager.discover()
        await plugin_manager.load()
        await plugin_manager.start()

        # Mount plugin routers
        for router, prefix, tags in plugin_manager.get_routers():
            app.include_router(router, prefix=prefix, tags=tags)

        logger.info(f"Plugin system initialized: {len(plugin_manager.get_loaded_plugins())} plugins loaded")

    # Start the background scheduler
    await task_scheduler.start()
    logger.info("Aegis Mesh Core started")

    yield

    # Shutdown: stop plugins, scheduler and cleanup
    if plugin_manager:
        await plugin_manager.stop()
        logger.info("Plugin system stopped")

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
app.include_router(plugins_router.router, prefix="/api/plugins", tags=["plugins"])
app.include_router(llm_router, prefix="/api/llm", tags=["llm"])

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
