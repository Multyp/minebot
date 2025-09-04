import discord
from discord import app_commands
from minecraft_utils import MinecraftUtils
from embed_utils import EmbedUtils
from config import Config

class BasicCommands:
    """Basic bot commands like status and seed"""
    
    def __init__(self, minecraft_utils: MinecraftUtils):
        self.minecraft_utils = minecraft_utils
    
    @app_commands.command(name="status", description="Check Minecraft server status")
    async def status(self, interaction: discord.Interaction):
        """Check the status of the Minecraft server"""
        try:
            server_status = self.minecraft_utils.get_server_status_sync()
            
            embed = EmbedUtils.create_server_status_embed(
                is_online=server_status.is_online,
                players_online=server_status.players_online,
                max_players=server_status.max_players,
                latency=server_status.latency
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            embed = EmbedUtils.create_error_embed(
                title="🔴 Server Status Error",
                message="❌ Failed to check server status"
            )
            await interaction.response.send_message(embed=embed)
            print(f"Error checking server status: {e}")
    
    @app_commands.command(name="seed", description="Get the Minecraft server seed")
    async def seed(self, interaction: discord.Interaction):
        """Display the server seed"""
        embed = EmbedUtils.create_seed_embed(Config.MC_SEED)
        await interaction.response.send_message(embed=embed)

def setup_basic_commands(tree: app_commands.CommandTree, minecraft_utils: MinecraftUtils):
    """Setup basic commands on the command tree"""
    basic_commands = BasicCommands(minecraft_utils)
    tree.add_command(basic_commands.status)
    tree.add_command(basic_commands.seed)
