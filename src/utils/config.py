"""
Configuration management for the role bot.
"""
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


class ConfigError(Exception):
    """Configuration-related errors."""
    pass


@dataclass
class Config:
    """Bot configuration."""
    discord_token: str
    guild_id: int
    role_channel_id: int
    log_channel_id: Optional[int]
    owner_role_id: Optional[int]
    roles_file: Path
    
    @classmethod
    def load(cls) -> 'Config':
        """Load configuration from environment."""
        load_dotenv()
        
        # Required configuration
        discord_token = os.getenv('DISCORD_TOKEN')
        if not discord_token:
            raise ConfigError("DISCORD_TOKEN not found in environment")
        
        guild_id = os.getenv('GUILD_ID')
        if not guild_id:
            raise ConfigError("GUILD_ID not found in environment")
        
        role_channel_id = os.getenv('ROLE_CHANNEL_ID')
        if not role_channel_id:
            raise ConfigError("ROLE_CHANNEL_ID not found in environment")
        
        # Optional configuration
        log_channel_id = os.getenv('LOG_CHANNEL_ID')
        owner_role_id = os.getenv('OWNER_ROLE_ID')
        roles_file = Path(os.getenv('ROLES_FILE', 'data/roles.json'))
        
        return cls(
            discord_token=discord_token,
            guild_id=int(guild_id),
            role_channel_id=int(role_channel_id),
            log_channel_id=int(log_channel_id) if log_channel_id else None,
            owner_role_id=int(owner_role_id) if owner_role_id else None,
            roles_file=roles_file
        )
