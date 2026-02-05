"""
Plugin base classes and data structures
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable, TYPE_CHECKING
from fastapi import APIRouter

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class PluginInfo:
    """Metadata about a plugin"""
    name: str
    version: str
    description: str
    author: str = ""
    homepage: str = ""
    requires: List[str] = field(default_factory=list)  # Required plugin dependencies


@dataclass
class PluginCapabilities:
    """What a plugin can provide"""
    routers: List[APIRouter] = field(default_factory=list)  # FastAPI routers to mount
    scheduled_jobs: List[Dict[str, Any]] = field(default_factory=list)  # APScheduler jobs
    event_hooks: Dict[str, List[Callable]] = field(default_factory=dict)  # Event type -> handlers


@dataclass
class PluginContext:
    """Context provided to plugins during initialization"""
    config: Dict[str, Any]  # Plugin-specific configuration
    get_db_session: Callable  # Function to get database session
    emit_event: Callable  # Function to emit events
    logger: Any  # Logger instance


class PluginBase(ABC):
    """
    Abstract base class for all Aegis Mesh plugins.

    Plugins must implement:
    - info property: Return PluginInfo with metadata
    - is_configured property: Return True if plugin has required configuration
    - initialize(): Called when plugin is loaded
    - start(): Called when plugin should begin operation
    - stop(): Called when plugin should cease operation

    Optionally override:
    - get_capabilities(): Return routers, jobs, and event hooks
    - get_status(): Return current plugin status
    - get_health(): Return health check information
    """

    _context: Optional[PluginContext] = None
    _initialized: bool = False
    _running: bool = False

    @property
    @abstractmethod
    def info(self) -> PluginInfo:
        """Return plugin metadata"""
        ...

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if plugin has all required configuration"""
        ...

    @abstractmethod
    async def initialize(self, context: PluginContext) -> bool:
        """
        Initialize the plugin with the provided context.

        Args:
            context: PluginContext with configuration and utilities

        Returns:
            True if initialization succeeded, False otherwise
        """
        ...

    @abstractmethod
    async def start(self) -> None:
        """Start plugin operation"""
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Stop plugin operation and cleanup"""
        ...

    def get_capabilities(self) -> PluginCapabilities:
        """
        Return plugin capabilities.
        Override to provide routers, scheduled jobs, or event hooks.
        """
        return PluginCapabilities()

    def get_status(self) -> Dict[str, Any]:
        """
        Return current plugin status.
        Override for custom status reporting.
        """
        return {
            "name": self.info.name,
            "version": self.info.version,
            "initialized": self._initialized,
            "running": self._running,
            "configured": self.is_configured,
        }

    async def get_health(self) -> Dict[str, Any]:
        """
        Return health check information.
        Override for custom health checks.
        """
        return {
            "healthy": self._running and self.is_configured,
            "details": {}
        }
