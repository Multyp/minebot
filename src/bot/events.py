"""
Discord bot event handlers and IPC integration.
"""

import discord
import logging

from ..services.location_manager import LocationManager
from ..ipc.events import EventBus, event_handler


class EventHandler:
    """Handles Discord events and integrates with the event bus system."""
    
    def __init__(self, client: discord.Client, event_bus: EventBus, location_manager: LocationManager):
        self.client = client
        self.event_bus = event_bus
        self.location_manager = location_manager
        self.logger = logging.getLogger(__name__)
        
        self._setup_event_handlers()
    
    def _setup_event_handlers(self):
        """Setup internal event handlers using the event bus."""
        
        @event_handler(self.event_bus, 'bot_ready')
        def on_bot_ready(event_name, data):
            self.logger.info(f"Bot ready event received: {data}")
        
        @event_handler(self.event_bus, 'locations_loaded')
        def on_locations_loaded(event_name, data):
            self.logger.info(f"Locations loaded: {data['location_count']} types, {data['total_instances']} instances")
        
        @event_handler(self.event_bus, 'location_instance_added')
        def on_location_added(event_name, data):
            self.logger.info(f"Location added: {data['location_name']} #{data['instance_index']}")
        
        @event_handler(self.event_bus, 'location_instance_removed')
        def on_location_instance_removed(event_name, data):
            self.logger.info(f"Location instance removed: {data['location_name']} #{data['instance_index']}")
        
        @event_handler(self.event_bus, 'location_removed')
        def on_location_removed(event_name, data):
            self.logger.info(f"Location removed: {data['location_name']} ({data['instance_count']} instances)")
        
        @event_handler(self.event_bus, 'location_status_updated')
        def on_location_status_updated(event_name, data):
            status = "looted" if data['new_looted'] else "available"
            self.logger.info(f"Location status updated: {data['location_name']} #{data['instance_index']} -> {status}")
        
        @event_handler(self.event_bus, 'server_status_updated')
        def on_server_status_updated(event_name, data):
            status = data['status']
            if status.online:
                self.logger.debug(f"Server online: {status.players_online}/{status.max_players} players, {status.latency:.1f}ms")
            else:
                self.logger.debug("Server offline")
        
        @event_handler(self.event_bus, 'server_status_failed')
        def on_server_status_failed(event_name, data):
            self.logger.warning(f"Server status check failed for {data['address']}: {data['error']}")
    
    async def on_error(self, event_name: str, *args, **kwargs):
        """Handle Discord client errors."""
        self.logger.error(f"Discord event error in '{event_name}': {args} {kwargs}")
        
        # Emit error event for other components to handle
        self.event_bus.emit('discord_error', {
            'event_name': event_name,
            'args': args,
            'kwargs': kwargs
        })
