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
class ServerConfig:
    """Server (host machine) login configuration."""
    host: str
    user: str
    password: str


@dataclass
class DiscordConfig:
    """Discord bot configuration."""
    token: str
    guild_id: Optional[int] = None
    alert_channel_id: Optional[int] = None
    log_channel_id: Optional[int] = None
    owner_role_id: Optional[int] = None

@dataclass
class Config:
    """Main application configuration."""
    discord: DiscordConfig
    minecraft: MinecraftConfig
    server: ServerConfig
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

        alert_channel_str = os.getenv("ALERT_CHANNEL_ID")
        alert_channel_id = int(alert_channel_str) if alert_channel_str else None

        log_channel_str = os.getenv("LOG_CHANNEL_ID")
        log_channel_id = int(log_channel_str) if log_channel_str else None

        owner_role_str = os.getenv("OWNER_ROLE_ID")
        owner_role_id = int(owner_role_str) if owner_role_str else None

        discord_config = DiscordConfig(
            token=token,
            guild_id=guild_id,
            alert_channel_id=alert_channel_id,
            log_channel_id=log_channel_id,
            owner_role_id=owner_role_id
        )

        # Minecraft configuration
        mc_host = os.getenv("MC_SERVER_HOST")
        if not mc_host:
            raise ConfigError("MC_SERVER_HOST environment variable is required")
        
        mc_port = int(os.getenv("MC_SERVER_PORT", "25565"))
        minecraft_config = MinecraftConfig(host=mc_host, port=mc_port)
        
        # Server (host machine) configuration
        server_host = os.getenv("SERVER_HOST")
        server_user = os.getenv("SERVER_USER")
        server_password = os.getenv("SERVER_PASSWORD")
        if not (server_host and server_user and server_password):
            raise ConfigError("SERVER_HOST, SERVER_USER, and SERVER_PASSWORD are required")
        
        server_config = ServerConfig(
            host=server_host,
            user=server_user,
            password=server_password
        )
        
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
            server=server_config,
            seed=seed,
            data_dir=data_dir
        )
