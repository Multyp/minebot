"""
Role management service with persistent storage.
"""
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional

from ..models.role_config import RoleConfig, RoleMessage
from ..services.storage import StorageService
from ..ipc.events import EventBus


class RoleManager:
    """Manages role configurations with persistent storage and event integration."""
    
    def __init__(self, data_dir: Path, event_bus: EventBus):
        self.data_dir = data_dir
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)
        
        self.storage = StorageService(data_dir / "roles.json")
        self._role_message: Optional[RoleMessage] = None
        self._emoji_to_role: Dict[str, RoleConfig] = {}
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize the role manager and load existing data."""
        try:
            data = await self.storage.load()
            await self._load_role_config(data)
            
            if self._role_message:
                self.logger.info(
                    f'✅ Loaded role configuration with {len(self._role_message.roles)} roles'
                )
            else:
                self.logger.info('📝 No existing role configuration found')
            
            self.event_bus.emit('roles_loaded', {
                'role_count': len(self._role_message.roles) if self._role_message else 0
            })
            
        except Exception as e:
            self.logger.error(f"Failed to initialize role manager: {e}")
            # Initialize with empty config
            self._role_message = None
            self._emoji_to_role = {}
    
    async def cleanup(self):
        """Cleanup resources."""
        await self._save_config()
    
    async def _load_role_config(self, data: Dict):
        """Load role configuration from storage data."""
        async with self._lock:
            if data:
                self._role_message = RoleMessage.from_dict(data)
                self._rebuild_emoji_map()
    
    def _rebuild_emoji_map(self):
        """Rebuild the emoji to role mapping."""
        self._emoji_to_role = {}
        if self._role_message:
            for role in self._role_message.roles:
                self._emoji_to_role[role.emoji] = role
    
    async def _save_config(self):
        """Save role configuration to storage."""
        if self._role_message:
            data = self._role_message.to_dict()
            await self.storage.save(data)
            
            self.event_bus.emit('roles_saved', {
                'role_count': len(self._role_message.roles)
            })
    
    # Public API methods
    
    async def set_role_message(self, message_id: int, channel_id: int, roles: List[RoleConfig]):
        """Set or update the role message configuration."""
        async with self._lock:
            self._role_message = RoleMessage(
                message_id=message_id,
                channel_id=channel_id,
                roles=roles
            )
            self._rebuild_emoji_map()
            
            await self._save_config()
            
            self.event_bus.emit('role_message_set', {
                'message_id': message_id,
                'channel_id': channel_id,
                'role_count': len(roles)
            })
    
    async def get_role_message(self) -> Optional[RoleMessage]:
        """Get the current role message configuration."""
        return self._role_message
    
    async def get_role_by_emoji(self, emoji: str) -> Optional[RoleConfig]:
        """Get role configuration by emoji."""
        return self._emoji_to_role.get(emoji)
    
    async def get_all_roles(self) -> List[RoleConfig]:
        """Get all configured roles."""
        if self._role_message:
            return self._role_message.roles.copy()
        return []
    
    async def has_role_message(self) -> bool:
        """Check if a role message is configured."""
        return self._role_message is not None
    
    async def get_message_id(self) -> Optional[int]:
        """Get the configured message ID."""
        return self._role_message.message_id if self._role_message else None
    
    async def clear_role_message(self):
        """Clear the role message configuration."""
        async with self._lock:
            self._role_message = None
            self._emoji_to_role = {}
            
            await self._save_config()
            
            self.event_bus.emit('role_message_cleared', {})
    
    async def backup_data(self) -> bool:
        """Create a backup of role data."""
        try:
            await self.storage.backup()
            self.event_bus.emit('roles_backed_up', {})
            return True
        except Exception as e:
            self.logger.error(f"Failed to backup role data: {e}")
            return False
