"""
Configuration management for the Minecraft Discord Bot.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

from .exceptions import ConfigError


load_dotenv()

@dataclass
class MinecraftConfig:
    """Minecraft server configuration."""
    host: str
    port: int = 25565
    
    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"


@dataclass
class DiscordConfig:
    """Discord bot configuration."""
    token: str
    guild_id: Optional[int] = None


@dataclass
class Config:
    """Main application configuration."""
    discord: DiscordConfig
    minecraft: MinecraftConfig
    seed: str
    data_dir: Path
    
    @classmethod
    def load(cls) -> 'Config':
        """Load configuration from environment variables."""
        # Discord configuration
        token = os.getenv("DISCORD_TOKEN")
        if not token:
            raise ConfigError("DISCORD_TOKEN environment variable is required")
        
        guild_id_str = os.getenv("DISCORD_GUILD_ID")
        guild_id = int(guild_id_str) if guild_id_str else None
        
        discord_config = DiscordConfig(token=token, guild_id=guild_id)
        
        # Minecraft configuration
        mc_host = os.getenv("MC_SERVER_HOST")
        if not mc_host:
            raise ConfigError("MC_SERVER_HOST environment variable is required")
        
        mc_port = int(os.getenv("MC_SERVER_PORT", "25565"))
        minecraft_config = MinecraftConfig(host=mc_host, port=mc_port)
        
        # Server seed
        seed = os.getenv("MC_SEED", "")
        if not seed:
            raise ConfigError("MC_SEED environment variable is required")
        
        # Data directory
        data_dir = Path(os.getenv("DATA_DIR", "data"))
        data_dir.mkdir(exist_ok=True)
        
        return cls(
            discord=discord_config,
            minecraft=minecraft_config,
            seed=seed,
            data_dir=data_dir
        )
