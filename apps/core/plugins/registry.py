"""
Event hooks registry for plugin communication
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Any, Awaitable

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Events that plugins can subscribe to"""
    # Task events
    TASK_CREATED = "task.created"
    TASK_UPDATED = "task.updated"
    TASK_COMPLETED = "task.completed"
    TASK_DUE = "task.due"
    TASK_OVERDUE = "task.overdue"
    TASK_SNOOZED = "task.snoozed"

    # Alert events
    ALERT_SENT = "alert.sent"
    ALERT_FAILED = "alert.failed"

    # System events
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"

    # Plugin events
    PLUGIN_LOADED = "plugin.loaded"
    PLUGIN_UNLOADED = "plugin.unloaded"


@dataclass
class EventHook:
    """A registered event handler"""
    event_type: EventType
    handler: Callable[[Dict[str, Any]], Awaitable[None]]
    plugin_name: str
    priority: int = 100  # Lower = higher priority


class EventRegistry:
    """
    Registry for event hooks.
    Allows plugins to subscribe to and emit events.
    """

    def __init__(self):
        self._hooks: Dict[EventType, List[EventHook]] = {}
        self._enabled = True

    def register(
        self,
        event_type: EventType,
        handler: Callable[[Dict[str, Any]], Awaitable[None]],
        plugin_name: str,
        priority: int = 100
    ) -> None:
        """Register an event handler"""
        if event_type not in self._hooks:
            self._hooks[event_type] = []

        hook = EventHook(
            event_type=event_type,
            handler=handler,
            plugin_name=plugin_name,
            priority=priority
        )
        self._hooks[event_type].append(hook)
        # Sort by priority (lower first)
        self._hooks[event_type].sort(key=lambda h: h.priority)

        logger.debug(f"Registered hook for {event_type.value} from {plugin_name}")

    def unregister(self, plugin_name: str) -> int:
        """
        Unregister all handlers for a plugin.
        Returns the number of hooks removed.
        """
        removed = 0
        for event_type in self._hooks:
            original_len = len(self._hooks[event_type])
            self._hooks[event_type] = [
                h for h in self._hooks[event_type]
                if h.plugin_name != plugin_name
            ]
            removed += original_len - len(self._hooks[event_type])

        if removed > 0:
            logger.debug(f"Unregistered {removed} hooks from {plugin_name}")

        return removed

    async def emit(self, event_type: EventType, data: Dict[str, Any]) -> None:
        """
        Emit an event to all registered handlers.
        Handlers are called in priority order.
        """
        if not self._enabled:
            return

        hooks = self._hooks.get(event_type, [])
        if not hooks:
            return

        logger.debug(f"Emitting {event_type.value} to {len(hooks)} handlers")

        for hook in hooks:
            try:
                await hook.handler(data)
            except Exception as e:
                logger.error(
                    f"Error in event handler {hook.plugin_name} for {event_type.value}: {e}"
                )

    def get_hooks(self, event_type: EventType) -> List[EventHook]:
        """Get all hooks for an event type"""
        return self._hooks.get(event_type, [])

    def get_all_hooks(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all registered hooks (for debugging/status)"""
        return {
            event_type.value: [
                {
                    "plugin": h.plugin_name,
                    "priority": h.priority
                }
                for h in hooks
            ]
            for event_type, hooks in self._hooks.items()
        }

    def clear(self) -> None:
        """Clear all registered hooks"""
        self._hooks.clear()

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable event emission"""
        self._enabled = enabled


# Global event registry instance
event_registry = EventRegistry()
