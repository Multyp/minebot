"""
Discord bot client for role management.
"""
import discord
from discord.ext import commands
import logging
from pathlib import Path
import traceback

from ..utils.config import Config
from ..services.role_manager import RoleManager
from ..ipc.events import EventBus


class RoleBot(commands.Bot):
    """Discord bot for managing role assignments through reactions."""
    
    def __init__(self, config: Config):
        intents = discord.Intents.default()
        intents.guilds = True
        intents.members = True
        intents.message_content = True
        intents.reactions = True
        
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Initialize IPC system
        self.event_bus = EventBus()
        
        # Initialize services
        data_dir = Path('data')
        data_dir.mkdir(exist_ok=True)
        
        self.role_manager = RoleManager(data_dir, self.event_bus)
    
    async def setup_hook(self):
        """Setup hook called when bot is starting."""
        # Initialize services
        await self.role_manager.initialize()
        
        # Load cogs
        try:
            await self.load_extension('src.bot.cogs.role_commands')
            self.logger.info("✅ Loaded cog: role_commands")
        except Exception as e:
            self.logger.error(f"❌ Failed to load cog role_commands: {e}")
            self.logger.error(traceback.format_exc())
        
        try:
            await self.load_extension('src.bot.cogs.role_reactions')
            self.logger.info("✅ Loaded cog: role_reactions")
        except Exception as e:
            self.logger.error(f"❌ Failed to load cog role_reactions: {e}")
            self.logger.error(traceback.format_exc())
        
        # Sync slash commands with Discord
        try:
            synced = await self.tree.sync()
            self.logger.info(f"✅ Synced {len(synced)} slash command(s)")
        except Exception as e:
            self.logger.error(f"❌ Failed to sync commands: {e}")
            self.logger.error(traceback.format_exc())
        
        self.logger.info("Bot setup complete")
        
        # List all registered commands
        self.logger.info(f"Registered commands: {[cmd.name for cmd in self.commands]}")
        self.logger.info(f"Registered slash commands: {[cmd.name for cmd in self.tree.get_commands()]}")

    async def _check_role_message(self):
        """Check if role message exists and is valid."""
        role_message = await self.role_manager.get_role_message()
        
        if not role_message:
            self.logger.info("No role message configured. Use !setup_roles to configure.")
            return
        
        try:
            guild = self.get_guild(self.config.guild_id)
            if not guild:
                self.logger.error("Guild not found")
                return
            
            channel = guild.get_channel(role_message.channel_id)
            if not channel:
                self.logger.warning("Role channel not found")
                return
            
            try:
                message = await channel.fetch_message(role_message.message_id)
                self.logger.info(f"✅ Role message found in #{channel.name}")
                
                # Ensure all reactions are present
                await self._ensure_reactions(message, role_message)
                
            except discord.NotFound:
                self.logger.warning("Role message not found. It may have been deleted.")
                
        except Exception as e:
            self.logger.error(f"Error checking role message: {e}")
    
    async def _ensure_reactions(self, message: discord.Message, role_message):
        """Ensure all required reactions are on the message."""
        existing_reactions = {str(reaction.emoji) for reaction in message.reactions}
        
        for role_config in role_message.roles:
            if role_config.emoji not in existing_reactions:
                try:
                    await message.add_reaction(role_config.emoji)
                    self.logger.info(f"Added missing reaction {role_config.emoji}")
                except Exception as e:
                    self.logger.error(f"Failed to add reaction {role_config.emoji}: {e}")
    
    async def close(self):
        """Cleanup and close the bot."""
        if self.is_closed():
            return
            
        self.logger.info("Shutting down bot...")
        
        try:
            # Cleanup services
            await self.role_manager.cleanup()
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
        
        # Close the bot
        try:
            await super().close()
        except Exception as e:
            self.logger.error(f"Error closing bot: {e}")
        
        self.logger.info("Bot shutdown complete")
 