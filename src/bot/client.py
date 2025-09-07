"""
Main Discord bot client with component management.
"""

import discord
from discord.ext import commands
import logging
from typing import Optional

from ..utils.config import Config
from ..services.location_manager import LocationManager
from ..services.minecraft import MinecraftService
from ..commands.server import ServerCommands
from ..commands.locations.group import LocationCommandGroup
from ..ipc.events import EventBus
from .events import EventHandler


class MinecraftBot:
    """Main bot client with component orchestration."""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize Discord client
        intents = discord.Intents.default()
        intents.message_content = True
        
        self.client = discord.Client(intents=intents)
        self.tree = discord.app_commands.CommandTree(self.client)
        
        # Initialize services
        self.event_bus = EventBus()
        self.location_manager = LocationManager(config.data_dir, self.event_bus)
        self.minecraft_service = MinecraftService(config.minecraft, self.event_bus)
        
        # Initialize command handlers
        self.server_commands = ServerCommands(
            self.tree, self.minecraft_service, config.seed
        )
        self.location_commands = LocationCommandGroup(
            self.tree, self.location_manager
        )
        
        # Initialize event handlers
        self.event_handler = EventHandler(
            self.client, self.event_bus, self.location_manager
        )
        
        self._setup_client_events()
    
    def _setup_client_events(self):
        """Setup Discord client event handlers."""
        
        @self.client.event
        async def on_ready():
            await self._on_ready()
        
        @self.client.event
        async def on_error(event_name, *args, **kwargs):
            await self.event_handler.on_error(event_name, *args, **kwargs)
    
    async def _on_ready(self):
        """Handle bot ready event."""
        self.logger.info(f'🤖 Bot is ready! Logged in as {self.client.user}')
        self.logger.info(f'🌐 Connected to {len(self.client.guilds)} guilds')
        
        # Sync commands
        try:
            if self.config.discord.guild_id:
                guild = discord.Object(id=self.config.discord.guild_id)
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                self.logger.info(f"Commands synced to guild {self.config.discord.guild_id}")
            else:
                await self.tree.sync()
                self.logger.info("Commands synced globally")
        except Exception as e:
            self.logger.error(f"Failed to sync commands: {e}")
        
        # Initialize services
        await self.location_manager.initialize()
        await self.minecraft_service.initialize()
        
        # Emit ready event
        self.event_bus.emit('bot_ready', {
            'user': self.client.user,
            'guilds': len(self.client.guilds)
        })
    
    async def start(self):
        """Start the bot."""
        try:
            await self.client.start(self.config.discord.token)
        except Exception as e:
            self.logger.error(f"Failed to start bot: {e}")
            raise
    
    async def close(self):
        """Gracefully shutdown the bot."""
        self.logger.info("Shutting down bot...")
        
        # Cleanup services
        await self.minecraft_service.cleanup()
        await self.location_manager.cleanup()
        
        # Close client
        if not self.client.is_closed():
            await self.client.close()
        
        self.logger.info("Bot shutdown complete")
