"""
Plugin manager for lifecycle management
"""

import logging
from typing import Dict, List, Optional, Any, Callable, Type

from .base import PluginBase, PluginInfo, PluginContext, PluginCapabilities
from .registry import EventType, event_registry
from .discovery import discover_all_plugins

logger = logging.getLogger(__name__)


class PluginManager:
    """
    Manages plugin discovery, lifecycle, and coordination.

    Lifecycle:
    1. discover() - Find all available plugins
    2. load() - Instantiate and initialize plugins
    3. start() - Start all enabled plugins
    4. stop() - Stop all plugins
    """

    def __init__(
        self,
        plugins_dir: str = "./plugins",
        auto_discover: bool = True,
        enabled_list: Optional[List[str]] = None,
        disabled_list: Optional[List[str]] = None,
        get_db_session: Optional[Callable] = None,
    ):
        self.plugins_dir = plugins_dir
        self.auto_discover = auto_discover
        self.enabled_list = enabled_list or []
        self.disabled_list = disabled_list or []
        self.get_db_session = get_db_session

        # Plugin storage
        self._discovered: Dict[str, Type[PluginBase]] = {}
        self._instances: Dict[str, PluginBase] = {}
        self._configs: Dict[str, Dict[str, Any]] = {}

    async def discover(self) -> List[str]:
        """
        Discover available plugins.
        Returns list of discovered plugin names.
        """
        plugin_classes = discover_all_plugins(
            self.plugins_dir,
            self.auto_discover
        )

        self._discovered.clear()
        names = []

        for plugin_class in plugin_classes:
            try:
                # Create temporary instance to get info
                temp_instance = plugin_class()
                info = temp_instance.info
                self._discovered[info.name] = plugin_class
                names.append(info.name)
                logger.info(f"Discovered plugin: {info.name} v{info.version}")
            except Exception as e:
                logger.error(f"Failed to get info from plugin class: {e}")

        return names

    def _should_load(self, plugin_name: str) -> bool:
        """Check if a plugin should be loaded based on enabled/disabled lists"""
        # If enabled_list is specified, only load plugins in that list
        if self.enabled_list:
            return plugin_name in self.enabled_list

        # If disabled_list is specified, don't load plugins in that list
        if self.disabled_list:
            return plugin_name not in self.disabled_list

        # Default: load all discovered plugins
        return True

    async def load(self, plugin_configs: Optional[Dict[str, Dict[str, Any]]] = None) -> Dict[str, bool]:
        """
        Load and initialize discovered plugins.

        Args:
            plugin_configs: Optional dict of plugin name -> config dict

        Returns:
            Dict of plugin name -> success boolean
        """
        if plugin_configs:
            self._configs.update(plugin_configs)

        results: Dict[str, bool] = {}

        for name, plugin_class in self._discovered.items():
            if not self._should_load(name):
                logger.info(f"Skipping disabled plugin: {name}")
                continue

            try:
                # Create instance
                instance = plugin_class()

                # Create context
                context = PluginContext(
                    config=self._configs.get(name, {}),
                    get_db_session=self.get_db_session or (lambda: None),
                    emit_event=self._create_emit_function(name),
                    logger=logging.getLogger(f"aegis.plugins.{name}")
                )

                # Initialize
                success = await instance.initialize(context)
                if success:
                    instance._initialized = True
                    instance._context = context
                    self._instances[name] = instance

                    # Register event hooks
                    capabilities = instance.get_capabilities()
                    self._register_hooks(name, capabilities)

                    logger.info(f"Loaded plugin: {name}")
                else:
                    logger.warning(f"Plugin initialization returned False: {name}")

                results[name] = success

            except Exception as e:
                logger.error(f"Failed to load plugin {name}: {e}")
                results[name] = False

        return results

    def _create_emit_function(self, plugin_name: str) -> Callable:
        """Create an emit function bound to a plugin name"""
        async def emit(event_type: EventType, data: Dict[str, Any]) -> None:
            data["_source_plugin"] = plugin_name
            await event_registry.emit(event_type, data)
        return emit

    def _register_hooks(self, plugin_name: str, capabilities: PluginCapabilities) -> None:
        """Register event hooks from plugin capabilities"""
        for event_type_str, handlers in capabilities.event_hooks.items():
            try:
                event_type = EventType(event_type_str)
                for handler in handlers:
                    event_registry.register(event_type, handler, plugin_name)
            except ValueError:
                logger.warning(f"Unknown event type: {event_type_str}")

    async def start(self) -> Dict[str, bool]:
        """
        Start all loaded plugins.
        Returns dict of plugin name -> success boolean.
        """
        results: Dict[str, bool] = {}

        for name, instance in self._instances.items():
            try:
                await instance.start()
                instance._running = True
                results[name] = True
                logger.info(f"Started plugin: {name}")
            except Exception as e:
                logger.error(f"Failed to start plugin {name}: {e}")
                results[name] = False

        # Emit system startup event
        await event_registry.emit(EventType.SYSTEM_STARTUP, {
            "plugins_started": [n for n, s in results.items() if s]
        })

        return results

    async def stop(self) -> None:
        """Stop all running plugins"""
        # Emit system shutdown event first
        await event_registry.emit(EventType.SYSTEM_SHUTDOWN, {
            "plugins_running": list(self._instances.keys())
        })

        for name, instance in list(self._instances.items()):
            try:
                await instance.stop()
                instance._running = False
                logger.info(f"Stopped plugin: {name}")
            except Exception as e:
                logger.error(f"Error stopping plugin {name}: {e}")

            # Unregister hooks
            event_registry.unregister(name)

    async def enable_plugin(self, name: str) -> bool:
        """Enable a disabled plugin"""
        if name in self._instances:
            return True  # Already loaded

        if name not in self._discovered:
            logger.warning(f"Plugin not discovered: {name}")
            return False

        # Remove from disabled list if present
        if name in self.disabled_list:
            self.disabled_list.remove(name)

        # Load and start the plugin
        plugin_class = self._discovered[name]

        try:
            instance = plugin_class()
            context = PluginContext(
                config=self._configs.get(name, {}),
                get_db_session=self.get_db_session or (lambda: None),
                emit_event=self._create_emit_function(name),
                logger=logging.getLogger(f"aegis.plugins.{name}")
            )

            success = await instance.initialize(context)
            if not success:
                return False

            instance._initialized = True
            instance._context = context
            self._instances[name] = instance

            capabilities = instance.get_capabilities()
            self._register_hooks(name, capabilities)

            await instance.start()
            instance._running = True

            await event_registry.emit(EventType.PLUGIN_LOADED, {"name": name})
            logger.info(f"Enabled plugin: {name}")
            return True

        except Exception as e:
            logger.error(f"Failed to enable plugin {name}: {e}")
            return False

    async def disable_plugin(self, name: str) -> bool:
        """Disable an enabled plugin"""
        if name not in self._instances:
            return True  # Already not loaded

        try:
            instance = self._instances[name]
            await instance.stop()
            instance._running = False

            event_registry.unregister(name)
            del self._instances[name]

            # Add to disabled list
            if name not in self.disabled_list:
                self.disabled_list.append(name)

            await event_registry.emit(EventType.PLUGIN_UNLOADED, {"name": name})
            logger.info(f"Disabled plugin: {name}")
            return True

        except Exception as e:
            logger.error(f"Failed to disable plugin {name}: {e}")
            return False

    def get_plugin(self, name: str) -> Optional[PluginBase]:
        """Get a loaded plugin instance by name"""
        return self._instances.get(name)

    def get_all_plugins(self) -> Dict[str, PluginBase]:
        """Get all loaded plugin instances"""
        return dict(self._instances)

    def get_discovered_plugins(self) -> List[str]:
        """Get list of discovered plugin names"""
        return list(self._discovered.keys())

    def get_loaded_plugins(self) -> List[str]:
        """Get list of loaded plugin names"""
        return list(self._instances.keys())

    def get_plugin_status(self, name: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific plugin"""
        if name in self._instances:
            return self._instances[name].get_status()
        elif name in self._discovered:
            return {
                "name": name,
                "discovered": True,
                "loaded": False,
                "reason": "disabled" if name in self.disabled_list else "not_loaded"
            }
        return None

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all discovered plugins"""
        status = {}

        for name in self._discovered:
            if name in self._instances:
                status[name] = self._instances[name].get_status()
            else:
                status[name] = {
                    "name": name,
                    "discovered": True,
                    "loaded": False,
                    "reason": "disabled" if name in self.disabled_list else "not_loaded"
                }

        return status

    def get_routers(self) -> List[tuple]:
        """
        Get all routers from loaded plugins.
        Returns list of (router, prefix, tags) tuples.
        """
        routers = []
        for name, instance in self._instances.items():
            capabilities = instance.get_capabilities()
            for router in capabilities.routers:
                prefix = f"/api/plugins/{name}"
                tags = [f"plugin:{name}"]
                routers.append((router, prefix, tags))
        return routers

    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """Get all scheduled jobs from loaded plugins"""
        jobs = []
        for name, instance in self._instances.items():
            capabilities = instance.get_capabilities()
            for job in capabilities.scheduled_jobs:
                job["plugin_name"] = name
                jobs.append(job)
        return jobs


# Global plugin manager instance (initialized in main.py)
plugin_manager: Optional[PluginManager] = None
