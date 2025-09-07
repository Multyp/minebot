"""
Event bus system for inter-component communication.
"""

import asyncio
import logging
from typing import Dict, List, Callable, Any
from collections import defaultdict


class EventBus:
    """Event-driven communication system for decoupled components."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._async_handlers: Dict[str, List[Callable]] = defaultdict(list)
    
    def subscribe(self, event_name: str, handler: Callable):
        """Subscribe to synchronous events."""
        self._handlers[event_name].append(handler)
        self.logger.debug(f"Subscribed {handler.__name__} to event '{event_name}'")
    
    def subscribe_async(self, event_name: str, handler: Callable):
        """Subscribe to asynchronous events."""
        self._async_handlers[event_name].append(handler)
        self.logger.debug(f"Subscribed async {handler.__name__} to event '{event_name}'")
    
    def unsubscribe(self, event_name: str, handler: Callable):
        """Unsubscribe from synchronous events."""
        if handler in self._handlers[event_name]:
            self._handlers[event_name].remove(handler)
            self.logger.debug(f"Unsubscribed {handler.__name__} from event '{event_name}'")
    
    def unsubscribe_async(self, event_name: str, handler: Callable):
        """Unsubscribe from asynchronous events."""
        if handler in self._async_handlers[event_name]:
            self._async_handlers[event_name].remove(handler)
            self.logger.debug(f"Unsubscribed async {handler.__name__} from event '{event_name}'")
    
    def emit(self, event_name: str, data: Any = None):
        """Emit synchronous event to all subscribers."""
        self.logger.debug(f"Emitting event '{event_name}' with data: {data}")
        
        # Call synchronous handlers
        for handler in self._handlers[event_name]:
            try:
                handler(event_name, data)
            except Exception as e:
                self.logger.error(f"Error in sync handler {handler.__name__} for event '{event_name}': {e}")
        
        # Schedule async handlers
        async_handlers = self._async_handlers[event_name]
        if async_handlers:
            try:
                # Try to get current loop, create task if one exists
                loop = asyncio.get_running_loop()
                for handler in async_handlers:
                    loop.create_task(self._call_async_handler(handler, event_name, data))
            except RuntimeError:
                # No event loop running, handlers will be skipped
                self.logger.warning(f"No event loop available for async handlers of event '{event_name}'")
    
    async def emit_async(self, event_name: str, data: Any = None):
        """Emit asynchronous event and wait for all handlers."""
        self.logger.debug(f"Emitting async event '{event_name}' with data: {data}")
        
        # Call synchronous handlers first
        for handler in self._handlers[event_name]:
            try:
                handler(event_name, data)
            except Exception as e:
                self.logger.error(f"Error in sync handler {handler.__name__} for event '{event_name}': {e}")
        
        # Call async handlers and wait for completion
        tasks = []
        for handler in self._async_handlers[event_name]:
            task = asyncio.create_task(self._call_async_handler(handler, event_name, data))
            tasks.append(task)
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _call_async_handler(self, handler: Callable, event_name: str, data: Any):
        """Call async handler with error handling."""
        try:
            await handler(event_name, data)
        except Exception as e:
            self.logger.error(f"Error in async handler {handler.__name__} for event '{event_name}': {e}")
    
    def get_subscribers(self, event_name: str) -> Dict[str, int]:
        """Get count of subscribers for an event."""
        return {
            'sync': len(self._handlers[event_name]),
            'async': len(self._async_handlers[event_name])
        }
    
    def list_events(self) -> List[str]:
        """List all events that have subscribers."""
        events = set(self._handlers.keys()) | set(self._async_handlers.keys())
        return sorted(events)
    
    def clear_subscribers(self, event_name: str = None):
        """Clear subscribers for specific event or all events."""
        if event_name:
            self._handlers[event_name].clear()
            self._async_handlers[event_name].clear()
            self.logger.info(f"Cleared all subscribers for event '{event_name}'")
        else:
            self._handlers.clear()
            self._async_handlers.clear()
            self.logger.info("Cleared all event subscribers")


# Decorator for easy event subscription
def event_handler(event_bus: EventBus, event_name: str, async_handler: bool = False):
    """Decorator for registering event handlers."""
    def decorator(func: Callable):
        if async_handler:
            event_bus.subscribe_async(event_name, func)
        else:
            event_bus.subscribe(event_name, func)
        return func
    return decorator
