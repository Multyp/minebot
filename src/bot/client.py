"""
Main Discord bot client with component management.
"""

import discord
from discord.ext import commands
import logging
from typing import Optional
import asyncio

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

        # Monitoring state (instance-specific)
        self._crash_monitor_task = None
        self._consecutive_failures = 0
        self._crash_alert_sent = False
        self._last_players = set()

        # Setup Discord client event callbacks
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

        # Start crash monitor background task
        if not self._crash_monitor_task:
            self._crash_monitor_task = asyncio.create_task(self._crash_monitor_loop())
        
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

        # Cancel crash monitor
        if self._crash_monitor_task:
            self._crash_monitor_task.cancel()
            try:
                await self._crash_monitor_task
            except Exception:
                pass
        
        # Cleanup services
        await self.minecraft_service.cleanup()
        await self.location_manager.cleanup()
        
        # Close client
        if not self.client.is_closed():
            await self.client.close()
        
        self.logger.info("Bot shutdown complete")

    async def _crash_monitor_loop(self):
        """Background task to monitor server availability, crash, and player activity."""
        check_interval = 30  # seconds between status checks
        failure_threshold = 4  # number of consecutive failures ( ~=2 minutes )
        channel_id = getattr(self.config.discord, 'alert_channel_id', None)
        self.logger.info("Starting crash monitor loop")
        await self.client.wait_until_ready()

        while not self.client.is_closed():
            try:
                status = await self.minecraft_service.get_server_status()
                if status.online:
                    # Reset counters if server recovered
                    if self._consecutive_failures >= failure_threshold and self._crash_alert_sent:
                        await self._send_recovery_alert(channel_id, status)
                    self._consecutive_failures = 0
                    self._crash_alert_sent = False

                    # Player activity monitoring
                    try:
                        names = await self.minecraft_service.get_player_names()
                        current = set(names)
                        joined = sorted(current - self._last_players)
                        left = sorted(self._last_players - current)
                        if joined or left:
                            await self._send_player_activity(channel_id, joined, left)
                        self._last_players = current
                    except Exception as e:
                        self.logger.debug(f"Player list fetch failed: {e}")
                else:
                    self._consecutive_failures += 1
                    if (self._consecutive_failures >= failure_threshold \
                        and not self._crash_alert_sent):
                        await self._send_crash_alert(channel_id)
                        self._crash_alert_sent = True
                    if self._last_players:
                        self._last_players.clear()
                await asyncio.sleep(check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Crash monitor loop error: {e}")
                await asyncio.sleep(check_interval)

    async def _send_player_activity(self, channel_id: Optional[int], joined, left):
        """Send player join/leave notifications to alert channel."""
        if not channel_id or (not joined and not left):
            return
        channel = self.client.get_channel(channel_id)
        if not channel:
            try:
                channel = await self.client.fetch_channel(channel_id)
            except Exception:
                return
        parts = []
        if joined:
            parts.append("🟢 Joined: " + ", ".join(f"`{n}`" for n in joined))
        if left:
            parts.append("🔴 Left: " + ", ".join(f"`{n}`" for n in left))
        try:
            await channel.send("\n".join(parts))
        except Exception as e:
            self.logger.debug(f"Failed to send player activity: {e}")

    async def _send_crash_alert(self, channel_id: Optional[int]):
        """Send an alert to the configured channel when server is considered crashed."""
        if not channel_id:
            self.logger.warning("Crash alert channel not configured; skipping crash alert.")
            return
        channel = self.client.get_channel(channel_id)
        if not channel:
            try:
                channel = await self.client.fetch_channel(channel_id)
            except Exception:
                self.logger.error(f"Unable to fetch crash alert channel {channel_id}")
                return
        try:
            await channel.send("⚠️ **Minecraft Server Crash Detected**\nThe server has been unreachable for the last 2 minutes.")
            self.logger.info("Crash alert sent")
        except Exception as e:
            self.logger.error(f"Failed to send crash alert: {e}")

    async def _send_recovery_alert(self, channel_id: Optional[int], status):
        """Send a recovery notification when server comes back online after crash."""
        if not channel_id:
            return
        channel = self.client.get_channel(channel_id)
        if not channel:
            try:
                channel = await self.client.fetch_channel(channel_id)
            except Exception:
                return
        try:
            await channel.send(
                f"✅ **Server Recovered**\nBack online with {status.players_online}/{status.max_players} players. Latency {status.latency:.1f}ms"
            )
            self.logger.info("Recovery alert sent")
        except Exception as e:
            self.logger.error(f"Failed to send recovery alert: {e}")
