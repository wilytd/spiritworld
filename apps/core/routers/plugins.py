"""
API endpoints for plugin management
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from plugins import PluginManager, event_registry

logger = logging.getLogger(__name__)
router = APIRouter()

# Will be set during app startup
_plugin_manager: Optional[PluginManager] = None


def set_plugin_manager(manager: PluginManager):
    """Set the plugin manager instance"""
    global _plugin_manager
    _plugin_manager = manager


def get_plugin_manager() -> PluginManager:
    """Get the plugin manager or raise 503"""
    if _plugin_manager is None:
        raise HTTPException(status_code=503, detail="Plugin system not initialized")
    return _plugin_manager


# Response schemas
class PluginInfo(BaseModel):
    name: str
    version: str
    description: str
    author: str
    homepage: str


class PluginStatus(BaseModel):
    name: str
    version: Optional[str] = None
    description: Optional[str] = None
    initialized: bool = False
    running: bool = False
    configured: bool = False
    discovered: bool = True
    loaded: bool = True
    reason: Optional[str] = None


class PluginListResponse(BaseModel):
    discovered: List[str]
    loaded: List[str]
    plugins: dict


class PluginDetailResponse(BaseModel):
    info: PluginInfo
    status: PluginStatus
    capabilities: dict
    health: Optional[dict] = None


class EnableDisableResponse(BaseModel):
    success: bool
    message: str


class EventHooksResponse(BaseModel):
    hooks: dict


@router.get("/", response_model=PluginListResponse)
async def list_plugins():
    """List all discovered and loaded plugins"""
    manager = get_plugin_manager()

    return PluginListResponse(
        discovered=manager.get_discovered_plugins(),
        loaded=manager.get_loaded_plugins(),
        plugins=manager.get_all_status(),
    )


@router.get("/hooks", response_model=EventHooksResponse)
async def get_event_hooks():
    """Get all registered event hooks"""
    return EventHooksResponse(hooks=event_registry.get_all_hooks())


@router.get("/{name}", response_model=PluginDetailResponse)
async def get_plugin_details(name: str):
    """Get detailed information about a specific plugin"""
    manager = get_plugin_manager()

    plugin = manager.get_plugin(name)
    if not plugin:
        # Check if discovered but not loaded
        if name in manager.get_discovered_plugins():
            status = manager.get_plugin_status(name)
            raise HTTPException(
                status_code=404,
                detail=f"Plugin '{name}' is discovered but not loaded. Status: {status}"
            )
        raise HTTPException(status_code=404, detail=f"Plugin '{name}' not found")

    info = plugin.info
    capabilities = plugin.get_capabilities()
    health = await plugin.get_health()

    return PluginDetailResponse(
        info=PluginInfo(
            name=info.name,
            version=info.version,
            description=info.description,
            author=info.author,
            homepage=info.homepage,
        ),
        status=PluginStatus(**plugin.get_status()),
        capabilities={
            "routers": len(capabilities.routers),
            "scheduled_jobs": len(capabilities.scheduled_jobs),
            "event_hooks": {k: len(v) for k, v in capabilities.event_hooks.items()},
        },
        health=health,
    )


@router.post("/{name}/enable", response_model=EnableDisableResponse)
async def enable_plugin(name: str):
    """Enable a disabled plugin"""
    manager = get_plugin_manager()

    if name not in manager.get_discovered_plugins():
        raise HTTPException(status_code=404, detail=f"Plugin '{name}' not discovered")

    if name in manager.get_loaded_plugins():
        return EnableDisableResponse(
            success=True,
            message=f"Plugin '{name}' is already enabled"
        )

    success = await manager.enable_plugin(name)

    if success:
        return EnableDisableResponse(
            success=True,
            message=f"Plugin '{name}' enabled successfully"
        )
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to enable plugin '{name}'"
        )


@router.post("/{name}/disable", response_model=EnableDisableResponse)
async def disable_plugin(name: str):
    """Disable an enabled plugin"""
    manager = get_plugin_manager()

    if name not in manager.get_discovered_plugins():
        raise HTTPException(status_code=404, detail=f"Plugin '{name}' not discovered")

    if name not in manager.get_loaded_plugins():
        return EnableDisableResponse(
            success=True,
            message=f"Plugin '{name}' is already disabled"
        )

    success = await manager.disable_plugin(name)

    if success:
        return EnableDisableResponse(
            success=True,
            message=f"Plugin '{name}' disabled successfully"
        )
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to disable plugin '{name}'"
        )
