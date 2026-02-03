"""
System Status API Router
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import httpx
import time
import os

from database import get_db
from schemas import StatusResponse

router = APIRouter()

# Track service start time
START_TIME = time.time()

@router.get("/", response_model=StatusResponse)
async def get_system_status(db: AsyncSession = Depends(get_db)):
    """Get overall system status"""

    # Check database connectivity
    db_status = "disconnected"
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        pass

    # Check mesh bridge connectivity
    mesh_status = "disconnected"
    mesh_url = os.getenv("MESH_BRIDGE_URL", "http://mesh-bridge:8001")
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{mesh_url}/health")
            if response.status_code == 200:
                mesh_status = "connected"
    except Exception:
        pass

    return StatusResponse(
        service="Aegis Mesh Core",
        version="0.1.0",
        database=db_status,
        mesh_bridge=mesh_status,
        uptime_seconds=time.time() - START_TIME
    )

@router.get("/services")
async def get_services_status():
    """Get status of all integrated services"""
    services = {}

    # Check mesh bridge
    mesh_url = os.getenv("MESH_BRIDGE_URL", "http://mesh-bridge:8001")
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{mesh_url}/status")
            services["mesh_bridge"] = response.json() if response.status_code == 200 else {"status": "error"}
    except Exception as e:
        services["mesh_bridge"] = {"status": "unreachable", "error": str(e)}

    return {"services": services}
