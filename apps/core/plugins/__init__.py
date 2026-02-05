"""
Aegis Mesh Plugin System

Provides extensibility through a plugin architecture with:
- Abstract base class for plugins
- Plugin manager for lifecycle management
- Event hooks for plugin communication
- Discovery from entry points and local directories
"""

from .base import PluginBase, PluginInfo, PluginCapabilities, PluginContext
from .manager import PluginManager
from .registry import EventType, EventHook, event_registry

__all__ = [
    "PluginBase",
    "PluginInfo",
    "PluginCapabilities",
    "PluginContext",
    "PluginManager",
    "EventType",
    "EventHook",
    "event_registry",
]
