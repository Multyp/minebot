from mcstatus import JavaServer
from typing import Optional, Tuple
from dataclasses import dataclass

@dataclass
class ServerStatus:
    """Represents Minecraft server status information"""
    is_online: bool
    players_online: int = 0
    max_players: int = 0
    latency: float = 0.0
    error_message: Optional[str] = None

class MinecraftUtils:
    """Utility class for Minecraft server operations"""
    
    def __init__(self, server_ip: str, server_port: int):
        self.server_ip = server_ip
        self.server_port = server_port
        self.server_address = f"{server_ip}:{server_port}"
    
    async def get_server_status(self) -> ServerStatus:
        """
        Get the current status of the Minecraft server.
        Returns ServerStatus object with connection information.
        """
        try:
            server = JavaServer.lookup(self.server_address)
            status = await self._query_server_async(server)
            
            return ServerStatus(
                is_online=True,
                players_online=status.players.online,
                max_players=status.players.max,
                latency=status.latency
            )
            
        except Exception as e:
            return ServerStatus(
                is_online=False,
                error_message=str(e)
            )
    
    def get_server_status_sync(self) -> ServerStatus:
        """
        Synchronous version of get_server_status for compatibility.
        """
        try:
            server = JavaServer.lookup(self.server_address)
            status = server.status()
            
            return ServerStatus(
                is_online=True,
                players_online=status.players.online,
                max_players=status.players.max,
                latency=status.latency
            )
            
        except Exception as e:
            return ServerStatus(
                is_online=False,
                error_message=str(e)
            )
    
    async def _query_server_async(self, server):
        """
        Internal method to query server status asynchronously.
        Falls back to sync if async is not available.
        """
        try:
            # Try async status if available
            if hasattr(server, 'async_status'):
                return await server.async_status()
            else:
                # Fall back to sync status
                return server.status()
        except Exception:
            # Final fallback to sync status
            return server.status()
    
    def format_teleport_command(self, x: int, y: int, z: int) -> str:
        """Format coordinates into a Minecraft teleport command"""
        return f"/tp {x} {y} {z}"
    
    def format_seed_command(self, seed: str) -> str:
        """Format seed into a Minecraft seed command"""
        return f"/seed {seed}"
    
    @staticmethod
    def validate_coordinates(x: int, y: int, z: int) -> Tuple[bool, str]:
        """
        Validate Minecraft coordinates.
        Returns (is_valid, error_message)
        """
        # Minecraft world boundaries (approximate)
        MAX_COORD = 30000000
        MIN_COORD = -30000000
        MAX_Y = 320
        MIN_Y = -64
        
        if not (MIN_COORD <= x <= MAX_COORD):
            return False, f"X coordinate {x} is outside valid range ({MIN_COORD} to {MAX_COORD})"
        
        if not (MIN_COORD <= z <= MAX_COORD):
            return False, f"Z coordinate {z} is outside valid range ({MIN_COORD} to {MAX_COORD})"
        
        if not (MIN_Y <= y <= MAX_Y):
            return False, f"Y coordinate {y} is outside valid range ({MIN_Y} to {MAX_Y})"
        
        return True, ""
    
    @staticmethod
    def format_coordinates(x: int, y: int, z: int) -> str:
        """Format coordinates for display"""
        return f"{x}, {y}, {z}"
