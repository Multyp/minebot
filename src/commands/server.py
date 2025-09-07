"""
Server-related Discord commands.
"""

import discord
from discord import app_commands
import logging

from ..services.minecraft import MinecraftService
from ..utils.embeds import EmbedBuilder


class ServerCommands:
    """Handles server status and information commands."""
    
    def __init__(self, tree: app_commands.CommandTree, minecraft_service: MinecraftService, seed: str):
        self.tree = tree
        self.minecraft_service = minecraft_service
        self.seed = seed
        self.logger = logging.getLogger(__name__)
        
        self._register_commands()
    
    def _register_commands(self):
        """Register all server commands with the command tree."""
        
        @self.tree.command(name="status", description="Check Minecraft server status")
        async def status_command(interaction: discord.Interaction):
            await self._handle_status(interaction)
        
        @self.tree.command(name="seed", description="Get the Minecraft server seed")
        async def seed_command(interaction: discord.Interaction):
            await self._handle_seed(interaction)
    
    async def _handle_status(self, interaction: discord.Interaction):
        """Handle server status command."""
        try:
            await interaction.response.defer()
            
            status = await self.minecraft_service.get_server_status()
            embed = EmbedBuilder.server_status_embed(
                online=status.online,
                players_online=status.players_online,
                max_players=status.max_players,
                latency=status.latency
            )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in status command: {e}")
            
            error_embed = EmbedBuilder.create_base_embed(
                title="❌ Error",
                description="Failed to retrieve server status. Please try again later.",
                color=discord.Color.red()
            )
            
            try:
                if interaction.response.is_done():
                    await interaction.followup.send(embed=error_embed, ephemeral=True)
                else:
                    await interaction.response.send_message(embed=error_embed, ephemeral=True)
            except:
                pass  # Interaction may have expired
    
    async def _handle_seed(self, interaction: discord.Interaction):
        """Handle seed command."""
        try:
            embed = EmbedBuilder.seed_embed(self.seed)
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in seed command: {e}")
            
            error_embed = EmbedBuilder.create_base_embed(
                title="❌ Error",
                description="Failed to retrieve server seed.",
                color=discord.Color.red()
            )
            
            try:
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
            except:
                pass  # Interaction may have expired
