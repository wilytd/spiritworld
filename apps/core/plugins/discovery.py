"""
Plugin discovery from entry points and local directories
"""

import importlib
import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import List, Type, Optional

from .base import PluginBase

logger = logging.getLogger(__name__)


def discover_entry_point_plugins() -> List[Type[PluginBase]]:
    """
    Discover plugins registered via setuptools entry points.
    Looks for the 'aegis.plugins' group.
    """
    plugins: List[Type[PluginBase]] = []

    try:
        if sys.version_info >= (3, 10):
            from importlib.metadata import entry_points
            eps = entry_points(group="aegis.plugins")
        else:
            from importlib.metadata import entry_points
            eps = entry_points().get("aegis.plugins", [])

        for ep in eps:
            try:
                plugin_class = ep.load()
                if isinstance(plugin_class, type) and issubclass(plugin_class, PluginBase):
                    plugins.append(plugin_class)
                    logger.info(f"Discovered entry point plugin: {ep.name}")
                else:
                    logger.warning(
                        f"Entry point {ep.name} does not point to a PluginBase subclass"
                    )
            except Exception as e:
                logger.error(f"Failed to load entry point plugin {ep.name}: {e}")

    except Exception as e:
        logger.error(f"Failed to enumerate entry points: {e}")

    return plugins


def discover_local_plugins(plugins_dir: str) -> List[Type[PluginBase]]:
    """
    Discover plugins from a local directory.
    Each plugin should be a Python file or package with a 'Plugin' class.
    """
    plugins: List[Type[PluginBase]] = []
    plugins_path = Path(plugins_dir)

    if not plugins_path.exists():
        logger.debug(f"Local plugins directory does not exist: {plugins_dir}")
        return plugins

    if not plugins_path.is_dir():
        logger.warning(f"Plugins path is not a directory: {plugins_dir}")
        return plugins

    # Add plugins directory to path if not already there
    plugins_dir_str = str(plugins_path.absolute())
    if plugins_dir_str not in sys.path:
        sys.path.insert(0, plugins_dir_str)

    for item in plugins_path.iterdir():
        plugin_class = None

        try:
            if item.is_file() and item.suffix == ".py" and not item.name.startswith("_"):
                # Single file plugin
                plugin_class = _load_plugin_from_file(item)

            elif item.is_dir() and (item / "__init__.py").exists():
                # Package plugin
                plugin_class = _load_plugin_from_package(item)

            if plugin_class is not None:
                plugins.append(plugin_class)
                logger.info(f"Discovered local plugin: {item.name}")

        except Exception as e:
            logger.error(f"Failed to load local plugin {item.name}: {e}")

    return plugins


def _load_plugin_from_file(filepath: Path) -> Optional[Type[PluginBase]]:
    """Load a plugin from a single Python file"""
    module_name = filepath.stem

    spec = importlib.util.spec_from_file_location(module_name, filepath)
    if spec is None or spec.loader is None:
        logger.warning(f"Could not load spec for {filepath}")
        return None

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    return _find_plugin_class(module, module_name)


def _load_plugin_from_package(package_path: Path) -> Optional[Type[PluginBase]]:
    """Load a plugin from a package directory"""
    module_name = package_path.name

    spec = importlib.util.spec_from_file_location(
        module_name,
        package_path / "__init__.py",
        submodule_search_locations=[str(package_path)]
    )
    if spec is None or spec.loader is None:
        logger.warning(f"Could not load spec for {package_path}")
        return None

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    return _find_plugin_class(module, module_name)


def _find_plugin_class(module, module_name: str) -> Optional[Type[PluginBase]]:
    """Find a PluginBase subclass in a module"""
    # First look for a class named 'Plugin'
    if hasattr(module, "Plugin"):
        cls = getattr(module, "Plugin")
        if isinstance(cls, type) and issubclass(cls, PluginBase) and cls is not PluginBase:
            return cls

    # Then look for any PluginBase subclass
    for attr_name in dir(module):
        if attr_name.startswith("_"):
            continue
        attr = getattr(module, attr_name)
        if (
            isinstance(attr, type)
            and issubclass(attr, PluginBase)
            and attr is not PluginBase
        ):
            return attr

    logger.warning(f"No PluginBase subclass found in {module_name}")
    return None


def discover_all_plugins(
    plugins_dir: str,
    auto_discover: bool = True
) -> List[Type[PluginBase]]:
    """
    Discover all plugins from entry points and local directory.

    Args:
        plugins_dir: Path to local plugins directory
        auto_discover: Whether to discover from entry points

    Returns:
        List of discovered plugin classes
    """
    plugins: List[Type[PluginBase]] = []

    if auto_discover:
        plugins.extend(discover_entry_point_plugins())

    plugins.extend(discover_local_plugins(plugins_dir))

    return plugins
