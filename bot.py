#!/usr/bin/env python3
"""
Minecraft Discord Bot - Main Entry Point

A Discord bot for managing Minecraft server status and locations.
"""

import discord
from discord import app_commands
import asyncio
import logging

# Import our modules
from config import Config
from location_manager import LocationManager
from minecraft_utils import MinecraftUtils
from commands.basic_commands import setup_basic_commands
from commands.location_commands import setup_location_commands

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MinecraftBot(discord.Client):
    """Main Discord bot client"""
    
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(intents=intents)
        
        # Initialize components
        self.config = Config()
        self.location_manager = LocationManager(self.config.LOCATIONS_FILE)
        self.minecraft_utils = MinecraftUtils(
            self.config.MC_SERVER_IP, 
            self.config.MC_SERVER_PORT
        )
        
        # Setup command tree
        self.tree = app_commands.CommandTree(self)
        self._setup_commands()
    
    def _setup_commands(self):
        """Setup all bot commands"""
        # Setup basic commands (status, seed)
        setup_basic_commands(self.tree, self.minecraft_utils)
        
        # Setup location commands (/locate group)
        setup_location_commands(self.tree, self.location_manager)
        
        logger.info("Commands setup completed")
    
    async def setup_hook(self):
        """Called when the bot is starting up"""
        try:
            # Validate configuration
            self.config.validate()
            
            # Sync commands to guild
            guild = discord.Object(id=self.config.GUILD_ID)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            
            logger.info("Commands synced successfully")
            
        except Exception as e:
            logger.error(f"Error in setup_hook: {e}")
            raise
    
    async def on_ready(self):
        """Called when the bot has successfully connected to Discord"""
        logger.info(f'🤖 Bot is ready! Logged in as {self.user}')
        logger.info(f'🌐 Connected to {len(self.guilds)} guilds')
        
        # Log location statistics
        location_types, total_instances, available, looted = self.location_manager.get_statistics()
        logger.info(f'📍 Loaded {location_types} location types with {total_instances} total instances')
        logger.info(f'💎 Available: {available}, 🏴‍☠️ Looted: {looted}')
        
        # Test server connection (optional)
        try:
            server_status = self.minecraft_utils.get_server_status_sync()
            if server_status.is_online:
                logger.info(f'⚡ Minecraft server is online ({server_status.players_online}/{server_status.max_players} players)')
            else:
                logger.warning('⚠️ Minecraft server appears to be offline')
        except Exception as e:
            logger.warning(f'⚠️ Could not check Minecraft server status: {e}')
    
    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle application command errors"""
        logger.error(f"Command error in {interaction.command}: {error}")
        
        # Create a generic error response
        embed = discord.Embed(
            title="❌ Command Error",
            description="An error occurred while processing your command. Please try again later.",
            color=discord.Color.red()
        )
        embed.set_footer(text="🎮 Gooner Status")
        
        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as followup_error:
            logger.error(f"Error sending error response: {followup_error}")

async def main():
    """Main function to run the bot"""
    try:
        # Create and run the bot
        bot = MinecraftBot()
        
        logger.info("Starting Minecraft Discord Bot...")
        await bot.start(bot.config.TOKEN)
        
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise
    finally:
        logger.info("Bot shutdown complete")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Failed to start bot: {e}")
