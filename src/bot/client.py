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

    async def on_ready(self):
        """Called when the bot is ready."""
        self.logger.info(f"✅ Bot logged in as {self.user}")
        
        # Automatically setup or verify role message
        await self._setup_role_message()
    
    async def _setup_role_message(self):
        """Automatically setup or verify the role message."""
        try:
            role_message_config = await self.role_manager.get_role_message()
            
            if not role_message_config or not role_message_config.channel_id:
                self.logger.info("No channel configured for role message")
                return
            
            # Get the configured channel
            channel = self.get_channel(role_message_config.channel_id)
            if not channel:
                self.logger.error(f"Channel {role_message_config.channel_id} not found")
                return
            
            guild = channel.guild
            
            # Check if message exists and is valid
            message_exists = False
            if role_message_config.message_id and role_message_config.message_id != 0:
                try:
                    message = await channel.fetch_message(role_message_config.message_id)
                    message_exists = True
                    self.logger.info(f"✅ Role message found in #{channel.name}")
                    
                    # Ensure all reactions are present
                    await self._ensure_reactions(message, role_message_config)
                except discord.NotFound:
                    self.logger.info("Role message not found, will create a new one")
                    message_exists = False
            
            # Create new message if needed
            if not message_exists:
                self.logger.info("Creating new role message...")
                
                # Ensure roles exist
                for role_config in role_message_config.roles:
                    if role_config.role_id == 0:
                        # Find or create the role
                        role = discord.utils.get(guild.roles, name=role_config.role_name)
                        if not role:
                            try:
                                role = await guild.create_role(
                                    name=role_config.role_name,
                                    mentionable=True,
                                    reason="Created by role bot"
                                )
                                self.logger.info(f"Created role: {role_config.role_name}")
                            except Exception as e:
                                self.logger.error(f"Failed to create role {role_config.role_name}: {e}")
                                continue
                        role_config.role_id = role.id
                
                # Load message content from markdown file
                message_file = Path('data/role_message.md')
                if message_file.exists():
                    with open(message_file, 'r', encoding='utf-8') as f:
                        message_content = f.read()
                else:
                    message_content = "# 🎭 Role Assignment\n\nReact to this message to get your roles!"
                
                # Build role descriptions
                role_descriptions = []
                for role_config in role_message_config.roles:
                    role = guild.get_role(role_config.role_id)
                    role_descriptions.append(
                        f"{role_config.emoji} **{role_config.role_name}** - {role_config.description}"
                    )
                
                # Combine message content with role descriptions
                full_message = message_content

                # Send the message
                message = await channel.send(full_message)
                
                # Add reactions
                for role_config in role_message_config.roles:
                    await message.add_reaction(role_config.emoji)
                
                # Save the message ID
                await self.role_manager.set_role_message(
                    message.id,
                    channel.id,
                    role_message_config.roles
                )
                
                self.logger.info(f"✅ Created role message in #{channel.name} (ID: {message.id})")
                
        except Exception as e:
            self.logger.error(f"Error setting up role message: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

    async def _check_role_message(self):
        """Check if role message exists and is valid (deprecated - now automatic)."""
        pass
    
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
 