"""
Minecraft server integration service.
"""

import asyncio
import logging
from dataclasses import dataclass
from typing import Optional

from mcstatus import JavaServer

from ..utils.config import MinecraftConfig
from ..utils.exceptions import MinecraftServerError
from ..ipc.events import EventBus


@dataclass
class ServerStatus:
    """Server status information."""
    online: bool
    players_online: int = 0
    max_players: int = 0
    latency: float = 0.0
    version: Optional[str] = None
    description: Optional[str] = None


class MinecraftService:
    """Handles Minecraft server interactions."""
    
    def __init__(self, config: MinecraftConfig, event_bus: EventBus):
        self.config = config
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
        
        self._server: Optional[JavaServer] = None
        self._last_status: Optional[ServerStatus] = None
    
    async def initialize(self):
        """Initialize the Minecraft service."""
        try:
            self._server = JavaServer.lookup(self.config.address)
            self.logger.info(f"Initialized Minecraft server connection to {self.config.address}")
        except Exception as e:
            self.logger.error(f"Failed to initialize Minecraft server connection: {e}")
            raise MinecraftServerError(f"Connection initialization failed: {e}")
    
    async def cleanup(self):
        """Cleanup resources."""
        self._server = None
        self._last_status = None
    
    async def get_server_status(self) -> ServerStatus:
        """Get current server status."""
        if not self._server:
            raise MinecraftServerError("Server not initialized")
        
        try:
            # Run in executor to prevent blocking
            loop = asyncio.get_event_loop()
            status = await loop.run_in_executor(None, self._server.status)
            
            server_status = ServerStatus(
                online=True,
                players_online=status.players.online,
                max_players=status.players.max,
                latency=status.latency,
                version=getattr(status.version, 'name', None),
                description=getattr(status, 'description', None)
            )
            
            # Emit status update event
            self.event_bus.emit('server_status_updated', {
                'status': server_status,
                'address': self.config.address
            })
            
            self._last_status = server_status
            return server_status
            
        except Exception as e:
            self.logger.warning(f"Server status check failed: {e}")
            
            server_status = ServerStatus(online=False)
            self._last_status = server_status
            
            self.event_bus.emit('server_status_failed', {
                'error': str(e),
                'address': self.config.address
            })
            
            return server_status
    
    async def ping_server(self) -> float:
        """Ping the server and return latency."""
        if not self._server:
            raise MinecraftServerError("Server not initialized")
        
        try:
            loop = asyncio.get_event_loop()
            latency = await loop.run_in_executor(None, self._server.ping)
            
            self.event_bus.emit('server_pinged', {
                'latency': latency,
                'address': self.config.address
            })
            
            return latency
            
        except Exception as e:
            self.logger.warning(f"Server ping failed: {e}")
            raise MinecraftServerError(f"Ping failed: {e}")
    
    async def query_server(self) -> dict:
        """Query server for detailed information."""
        if not self._server:
            raise MinecraftServerError("Server not initialized")
        
        try:
            loop = asyncio.get_event_loop()
            query = await loop.run_in_executor(None, self._server.query)
            
            query_data = {
                'players': {
                    'online': query.players.online,
                    'max': query.players.max,
                    'names': query.players.names
                },
                'software': query.software,
                'motd': query.motd,
                'map': query.map
            }
            
            self.event_bus.emit('server_queried', {
                'query_data': query_data,
                'address': self.config.address
            })
            
            return query_data
            
        except Exception as e:
            self.logger.warning(f"Server query failed: {e}")
            raise MinecraftServerError(f"Query failed: {e}")
    
    @property
    def last_known_status(self) -> Optional[ServerStatus]:
        """Get the last known server status."""
        return self._last_status
    
    @property
    def server_address(self) -> str:
        """Get the server address."""
        return self.config.address
