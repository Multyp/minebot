"""
Main Discord bot client with component management.
"""

import discord
from discord.ext import commands
import logging
from typing import Optional
import asyncio
import paramiko
import json
from pathlib import Path
import aiohttp

from ..utils.config import Config
from ..services.location_manager import LocationManager
from ..services.minecraft import MinecraftService
from ..commands.server import ServerCommands
from ..commands.locations.group import LocationCommandGroup
from ..ipc.events import EventBus
from .events import EventHandler
from ..const.advancements_names import ADVANCEMENT_NAMES

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
        self._advancement_monitor_task = None
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
        try:
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
            if not self._crash_monitor_task or self._crash_monitor_task.done():
                self._crash_monitor_task = asyncio.create_task(self._crash_monitor_loop())
                self.logger.info("Started crash monitor task")
            
            # DEBUG: Check advancement monitor task creation
            self.logger.info("=== DEBUGGING ADVANCEMENT TASK CREATION ===")
            self.logger.info(f"Has _advancement_monitor_task: {hasattr(self, '_advancement_monitor_task')}")
            if hasattr(self, "_advancement_monitor_task"):
                self.logger.info(f"Task value: {self._advancement_monitor_task}")
                if self._advancement_monitor_task:
                    self.logger.info(f"Task done: {self._advancement_monitor_task.done()}")
            
            # Start advancement monitor background task
            try:
                if not hasattr(self, "_advancement_monitor_task") or not self._advancement_monitor_task or self._advancement_monitor_task.done():
                    self.logger.info("Creating advancement monitor task...")
                    self._advancement_monitor_task = asyncio.create_task(self._advancement_monitor_loop())
                    self.logger.info(f"Created advancement monitor task: {self._advancement_monitor_task}")
                    
                    # Give it a moment and check if it's still alive
                    await asyncio.sleep(0.1)
                    if self._advancement_monitor_task.done():
                        self.logger.error(f"Advancement task died immediately! Exception: {self._advancement_monitor_task.exception()}")
                    else:
                        self.logger.info("Advancement monitor task created successfully and is running")
                else:
                    self.logger.info("Advancement monitor task already exists and is running")
            except Exception as e:
                self.logger.error(f"Error creating advancement monitor task: {e}", exc_info=True)
            
            # Emit ready event
            self.event_bus.emit('bot_ready', {
                'user': self.client.user,
                'guilds': len(self.client.guilds)
            })
            
        except Exception as e:
            self.logger.error(f"Error in _on_ready: {e}", exc_info=True)
        
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
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self.logger.error(f"Error cancelling crash monitor: {e}")
        
        # Cancel advancement monitor
        if hasattr(self, '_advancement_monitor_task') and self._advancement_monitor_task:
            self._advancement_monitor_task.cancel()
            try:
                await self._advancement_monitor_task
            except asyncio.CancelledError:
                pass
            except Exception as e:
                self.logger.error(f"Error cancelling advancement monitor: {e}")
        
        # Cleanup services
        await self.minecraft_service.cleanup()
        await self.location_manager.cleanup()
        
        # Close client
        if not self.client.is_closed():
            await self.client.close()
        
        self.logger.info("Bot shutdown complete")

    async def check_maintenance_flag(self, host, user, password):
        """Check if the maintenance flag file exists on the server."""
        loop = asyncio.get_running_loop()

        def _check():
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(host, username=user, password=password)
            stdin, stdout, stderr = ssh.exec_command(
                "test -f /tmp/mc_maintenance.flag && echo yes || echo no"
            )
            result = stdout.read().decode().strip()
            ssh.close()
            return result == "yes"

        return await loop.run_in_executor(None, _check)


    async def _crash_monitor_loop(self):
        """Background task to monitor server availability, crash, and player activity."""
        check_interval = 30  # seconds between status checks
        failure_threshold = 4  # number of consecutive failures ( ~=2 minutes )
        alert_channel_id = getattr(self.config.discord, 'alert_channel_id', None)
        log_channel_id = getattr(self.config.discord, 'log_channel_id', None)
        self.logger.info("Starting crash monitor loop")
        await self.client.wait_until_ready()

        while not self.client.is_closed():
            try:
                status = await self.minecraft_service.get_server_status()
                if status.online:
                    # Reset counters if server recovered
                    if self._consecutive_failures >= failure_threshold and self._crash_alert_sent:
                        await self._send_recovery_alert(alert_channel_id, status)
                    self._consecutive_failures = 0
                    self._crash_alert_sent = False

                    # Player activity monitoring
                    try:
                        names = await self.minecraft_service.get_player_names()
                        current = set(names)
                        joined = sorted(current - self._last_players)
                        left = sorted(self._last_players - current)
                        if joined or left:
                            await self._send_player_activity(log_channel_id, joined, left)
                        self._last_players = current
                    except Exception as e:
                        self.logger.debug(f"Player list fetch failed: {e}")

                else:
                    self._consecutive_failures += 1
                    if (self._consecutive_failures >= failure_threshold
                        and not self._crash_alert_sent):

                        # 🔹 Check if it's maintenance or a crash
                        if await self.check_maintenance_flag(self.config.server.host, self.config.server.user, self.config.server.password):
                            await self._send_message(alert_channel_id, "Server is in maintenance mode.")
                        else:
                            await self._send_crash_alert(alert_channel_id)

                        self._crash_alert_sent = True

                    if self._last_players:
                        self._last_players.clear()

                await asyncio.sleep(check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Crash monitor loop error: {e}")
                await asyncio.sleep(check_interval)

    async def _advancement_monitor_loop(self):
        """Background task to watch advancement files on remote server via SSH."""
        try:
            self.logger.info("=== REMOTE ADVANCEMENT MONITOR STARTING ===")
            
            check_interval = 15  # seconds
            # Use server config for SSH connection
            ssh_host = self.config.server.host
            ssh_user = self.config.server.user
            ssh_password = self.config.server.password
            world_dir = self.config.minecraft.world_dir
            server_dir = self.config.minecraft.server_dir
            
            self.logger.info(f"SSH Host: {ssh_host}")
            self.logger.info(f"SSH User: {ssh_user}")
            self.logger.info(f"Remote world dir: {world_dir}")
            
            # Test SSH connection first
            loop = asyncio.get_running_loop()
            
            def test_ssh_connection():
                try:
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(ssh_host, username=ssh_user, password=ssh_password, timeout=10)
                    
                    # Test if world directory exists
                    stdin, stdout, stderr = ssh.exec_command(f"test -d {world_dir} && echo 'EXISTS' || echo 'NOT_FOUND'")
                    result = stdout.read().decode().strip()
                    
                    # Test if advancements directory exists
                    stdin, stdout, stderr = ssh.exec_command(f"test -d {world_dir}/advancements && echo 'EXISTS' || echo 'NOT_FOUND'")
                    adv_result = stdout.read().decode().strip()
                    
                    # Test if whitelist exists
                    stdin, stdout, stderr = ssh.exec_command(f"test -f {server_dir}/whitelist.json && echo 'EXISTS' || echo 'NOT_FOUND'")
                    whitelist_result = stdout.read().decode().strip()
                    
                    ssh.close()
                    return result, adv_result, whitelist_result
                except Exception as e:
                    return None, None, str(e)
            
            world_exists, adv_exists, whitelist_exists = await loop.run_in_executor(None, test_ssh_connection)
            
            if isinstance(whitelist_exists, str) and "Exception" not in str(whitelist_exists):
                self.logger.info(f"Remote world directory exists: {world_exists == 'EXISTS'}")
                self.logger.info(f"Remote advancements directory exists: {adv_exists == 'EXISTS'}")
                self.logger.info(f"Remote whitelist.json exists: {whitelist_exists == 'EXISTS'}")
            else:
                self.logger.error(f"SSH connection failed: {whitelist_exists}")
                return
            
            if world_exists != 'EXISTS':
                self.logger.error(f"CRITICAL: World directory does not exist on remote server: {world_dir}")
                return
                
            if adv_exists != 'EXISTS':
                self.logger.error(f"CRITICAL: Advancements directory does not exist: {world_dir}/advancements")
                return

            # Load whitelist from remote server
            def load_remote_whitelist():
                try:
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(ssh_host, username=ssh_user, password=ssh_password, timeout=10)
                    
                    stdin, stdout, stderr = ssh.exec_command(f"cat {server_dir}/whitelist.json")
                    whitelist_content = stdout.read().decode().strip()
                    ssh.close()
                    
                    self.logger.info(f"Raw whitelist content (first 200 chars): {whitelist_content[:200]}")
                    
                    import json
                    whitelist_data = json.loads(whitelist_content)
                    self.logger.info(f"Parsed whitelist data type: {type(whitelist_data)}, length: {len(whitelist_data) if isinstance(whitelist_data, list) else 'N/A'}")
                    
                    if isinstance(whitelist_data, list):
                        result = {}
                        for entry in whitelist_data:
                            if isinstance(entry, dict) and "uuid" in entry and "name" in entry:
                                result[entry["uuid"]] = entry["name"]
                            else:
                                self.logger.warning(f"Invalid whitelist entry: {entry}")
                        self.logger.info(f"Successfully parsed {len(result)} players from whitelist")
                        return result
                    else:
                        self.logger.warning(f"Unexpected whitelist format: {type(whitelist_data)}")
                        return {}
                except json.JSONDecodeError as e:
                    self.logger.error(f"JSON decode error in whitelist: {e}")
                    return {}
                except Exception as e:
                    self.logger.error(f"Error loading whitelist: {e}")
                    return {}
            
            whitelist = await loop.run_in_executor(None, load_remote_whitelist)
            self.logger.info(f"Loaded {len(whitelist)} players from remote whitelist: {list(whitelist.values())}")

            seen = {}  # {uuid: set(advancement_keys)}
            advancements_channel_id = getattr(self.config.discord, "advancements_channel_id", None)
            
            self.logger.info(f"Advancements channel ID: {advancements_channel_id}")
            
            if not advancements_channel_id:
                self.logger.error("CRITICAL: No advancements channel configured, advancement monitoring disabled")
                return
                
            await self.client.wait_until_ready()
            
            # Verify Discord channel
            channel = self.client.get_channel(advancements_channel_id)
            if channel:
                self.logger.info(f"Found advancement channel: #{channel.name}")
            else:
                try:
                    channel = await self.client.fetch_channel(advancements_channel_id)
                    self.logger.info(f"Fetched advancement channel: #{channel.name}")
                except Exception as e:
                    self.logger.error(f"CRITICAL: Failed to fetch advancement channel: {e}")
                    return
            
            # Function to read advancement files from remote server
            def read_remote_advancements():
                try:
                    ssh = paramiko.SSHClient()
                    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    ssh.connect(ssh_host, username=ssh_user, password=ssh_password, timeout=10)
                    
                    # List all JSON files in advancements directory
                    stdin, stdout, stderr = ssh.exec_command(f"ls {world_dir}/advancements/*.json 2>/dev/null || echo 'NO_FILES'")
                    files_output = stdout.read().decode().strip()
                    
                    if files_output == 'NO_FILES':
                        ssh.close()
                        return {}
                    
                    files = files_output.split('\n')
                    advancements_data = {}
                    
                    for file_path in files:
                        if file_path.strip():
                            # Extract UUID from filename
                            uuid = file_path.split('/')[-1].replace('.json', '')
                            
                            # Read file content
                            stdin, stdout, stderr = ssh.exec_command(f"cat '{file_path}'")
                            file_content = stdout.read().decode()
                            
                            try:
                                data = json.loads(file_content)
                                advancements_data[uuid] = data
                            except json.JSONDecodeError as e:
                                continue  # Skip invalid JSON files
                    
                    ssh.close()
                    return advancements_data
                    
                except Exception as e:
                    return {}
            
            # Initialize seen data with current state
            initial_data = await loop.run_in_executor(None, read_remote_advancements)
            for uuid, data in initial_data.items():
                already = seen.setdefault(uuid, set())
                for adv_key, content in data.items():
                    try:
                        # Skip if content is not a dictionary (malformed data)
                        if not isinstance(content, dict):
                            self.logger.debug(f"Skipping malformed advancement {adv_key} for {uuid}: {type(content)}")
                            continue
                        if content.get("done"):
                            already.add(adv_key)
                    except Exception as e:
                        self.logger.debug(f"Error processing advancement {adv_key} for {uuid}: {e}")
                        continue
                player_name = whitelist.get(uuid, f"Unknown({uuid})")
                self.logger.info(f"Player {player_name} has {len(already)} completed advancements at startup")
            
            self.logger.info("=== REMOTE ADVANCEMENT MONITOR ACTIVE ===")

            loop_count = 0
            while not self.client.is_closed():
                try:
                    loop_count += 1
                    if loop_count % 20 == 0:  # Log every 5 minutes
                        self.logger.info(f"Remote advancement check #{loop_count}")
                    
                    # Read current advancement data from remote server
                    current_data = await loop.run_in_executor(None, read_remote_advancements)
                    
                    # Check for new completions
                    for uuid, data in current_data.items():
                        already = seen.setdefault(uuid, set())
                        for adv_key, content in data.items():
                            try:
                                # Skip if content is not a dictionary (malformed data)
                                if not isinstance(content, dict):
                                    continue
                                if content.get("done") and adv_key not in already:
                                    already.add(adv_key)
                                    player = whitelist.get(uuid, f"Unknown({uuid})")
                                    self.logger.info(f"🏆 NEW ADVANCEMENT: {player} completed {adv_key}")
                                    await self._send_advancement(advancements_channel_id, player, adv_key)
                            except Exception as e:
                                self.logger.debug(f"Error processing advancement {adv_key} for {uuid}: {e}")
                                continue

                    await asyncio.sleep(check_interval)

                except asyncio.CancelledError:
                    self.logger.info("Remote advancement monitor cancelled")
                    break
                except Exception as e:
                    self.logger.error(f"Remote advancement monitor error: {e}", exc_info=True)
                    await asyncio.sleep(check_interval)
                    
        except Exception as e:
            self.logger.error(f"CRITICAL: Remote advancement monitor failed to start: {e}", exc_info=True)

    def get_advancement_display_name(self, advancement_id):
        """Get the display name for an advancement, with fallback to formatted ID."""
        if advancement_id in ADVANCEMENT_NAMES:
            return ADVANCEMENT_NAMES[advancement_id]
        
        # Fallback: format the ID to be more readable
        # Remove minecraft: prefix and replace underscores with spaces, capitalize words
        clean_name = advancement_id.replace("minecraft:", "").replace("_", " ").title()
        return clean_name

    
    async def _send_advancement(self, channel_id: Optional[int], player: str, adv_key: str):
        """Send a Minecraft-themed advancement embed to Discord with player avatar."""
        self.logger.info(f"Attempting to send advancement: {player} -> {adv_key} to channel {channel_id}")
    
        if not channel_id:
            self.logger.error("No channel ID provided")
            return
            
        channel = self.client.get_channel(channel_id)
        if not channel:
            try:
                channel = await self.client.fetch_channel(channel_id)
            except Exception as e:
                self.logger.error(f"Failed to fetch channel {channel_id}: {e}")
                return
        
        # Get proper display name for the advancement
        display_name = self.get_advancement_display_name(adv_key)
        
        # Fetch player UUID from Mojang API
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://api.mojang.com/users/profiles/minecraft/{player}", timeout=5) as resp:
                    if resp.status != 200:
                        raise Exception(f"Mojang API returned {resp.status}")
                    data = await resp.json()
                    uuid_raw = data.get("id")
                    
                    # Format UUID with hyphens for Crafatar
                    if uuid_raw and len(uuid_raw) == 32:
                        uuid = f"{uuid_raw[:8]}-{uuid_raw[8:12]}-{uuid_raw[12:16]}-{uuid_raw[16:20]}-{uuid_raw[20:]}"
                        self.logger.debug(f"Formatted UUID for {player}: {uuid}")
                    else:
                        uuid = None
        except Exception as e:
            self.logger.warning(f"Could not fetch UUID for {player}: {e}")
            uuid = None
        
        # Build avatar URL if UUID exists - try multiple services
        avatar_url = None
        if uuid:
            # Try different avatar services that work better with Discord
            avatar_services = [
                f"https://mc-heads.net/avatar/{uuid}/64",
                f"https://crafatar.com/avatars/{uuid}/64.png",
                f"https://minotar.net/avatar/{uuid}/64.png"
            ]
            avatar_url = avatar_services[0]  # Use mc-heads.net as primary
        
        color = discord.Color.gold()
        
        try:
            embed = discord.Embed(
                title=f"🏆 {display_name}",
                description=f"**{player}** completed a Minecraft advancement!\n**{ADVANCEMENT_NAMES[adv_key]}**",
                color=color,
                timestamp=discord.utils.utcnow()
            )
            embed.set_footer(text=f"ID: {adv_key}")
        
            if avatar_url:
                embed.set_thumbnail(url=avatar_url)
                self.logger.debug(f"Setting avatar URL: {avatar_url}")
            
            message = await channel.send(embed=embed)
            self.logger.info(f"✅ Advancement message sent successfully (message ID: {message.id})")
        except Exception as e:
            self.logger.error(f"Failed to send advancement message: {e}", exc_info=True)
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
            # Create crash alert embed
            embed = discord.Embed(
                title="⚠️ Server Crash Detected",
                description="The Minecraft server has been unreachable for over 2 minutes.",
                color=discord.Color.red()
            )
            embed.add_field(
                name="🔍 Status",
                value="❌ **Offline**",
                inline=True
            )
            embed.add_field(
                name="⏱️ Duration",
                value="2+ minutes",
                inline=True
            )
            embed.add_field(
                name="🚨 Action Required",
                value="Server restart may be needed",
                inline=True
            )
            embed.set_footer(text="🎮 Gooner Status")
            
            # Send embed with role ping in spoiler
            await channel.send(
                content=f"||<@&{self.config.discord.owner_role_id}>||",
                embed=embed
            )
            self.logger.info("Crash alert sent")
        except Exception as e:
            self.logger.error(f"Failed to send crash alert: {e}")

    async def _send_message(self, channel_id: Optional[int], message: str):
        """Send a maintenance message to the specified channel."""
        if not channel_id:
            return
        channel = self.client.get_channel(channel_id)
        if not channel:
            try:
                channel = await self.client.fetch_channel(channel_id)
            except Exception:
                return
        try:
            # Create maintenance embed
            embed = discord.Embed(
                title="🔧 Server Maintenance",
                description="The Minecraft server is currently under maintenance.",
                color=discord.Color.orange()
            )
            embed.add_field(
                name="🔍 Status",
                value="🛠️ **Maintenance Mode**",
                inline=True
            )
            embed.add_field(
                name="⏱️ Expected Duration",
                value="Unknown",
                inline=True
            )
            embed.add_field(
                name="📝 Note",
                value="Server will return once maintenance is complete",
                inline=False
            )
            embed.set_footer(text="🎮 Gooner Status")
            
            # Send embed with role ping in spoiler
            await channel.send(
                content=f"||<@&{self.config.discord.owner_role_id}>||",
                embed=embed
            )
        except Exception as e:
            self.logger.error(f"Failed to send maintenance message: {e}")

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
            # Create recovery embed
            embed = discord.Embed(
                title="✅ Server Recovery",
                description="The Minecraft server has successfully recovered and is back online!",
                color=discord.Color.green()
            )
            embed.add_field(
                name="🔍 Status",
                value="🟢 **Online**",
                inline=True
            )
            embed.add_field(
                name="👥 Players",
                value=f"{status.players_online}/{status.max_players}",
                inline=True
            )
            embed.add_field(
                name="📡 Latency",
                value=f"{status.latency:.1f}ms",
                inline=True
            )
            embed.add_field(
                name="🎉 Welcome Back!",
                value="The server is ready for players",
                inline=False
            )
            embed.set_footer(text="🎮 Gooner Status")
            
            # Send embed with role ping in spoiler
            await channel.send(
                content=f"||<@&{self.config.discord.owner_role_id}>||",
                embed=embed
            )
            self.logger.info("Recovery alert sent")
        except Exception as e:
            self.logger.error(f"Failed to send recovery alert: {e}")