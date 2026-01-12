"""
Commands for managing role assignments.
"""
import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional

from ...models.role_config import RoleConfig


class RoleCommands(commands.Cog):
    """Commands for setting up and managing role assignments."""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
    
    @app_commands.command(name="setup_roles", description="Setup role assignment message")
    @app_commands.describe(
        channel="Channel to post the role message (defaults to current channel)"
    )
    @app_commands.default_permissions(administrator=True)
    async def setup_roles(
        self,
        interaction: discord.Interaction,
        channel: Optional[discord.TextChannel] = None
    ):
        """Setup the role assignment message."""
        await interaction.response.defer(ephemeral=True)
        
        target_channel = channel or interaction.channel
        
        # Check if message already exists
        if await self.bot.role_manager.has_role_message():
            role_message = await self.bot.role_manager.get_role_message()
            await interaction.followup.send(
                f"⚠️ A role message already exists (ID: {role_message.message_id}). "
                f"Use `/clear_roles` first to create a new one.",
                ephemeral=True
            )
            return
        
        # Define available roles (customize these!)
        roles_config = [
            RoleConfig(
                role_id=0,  # Will be set dynamically
                role_name="Tech Lab",
                emoji="💻",
                description="Get help or share your computer science projects"
            ),
            RoleConfig(
                role_id=0,
                role_name="Fashion",
                emoji="👗",
                description="Discuss fashion, style, and design"
            ),
            RoleConfig(
                role_id=0,
                role_name="Worldbuilding",
                emoji="🌍",
                description="Share and develop your creative worlds"
            )
        ]
        
        # Find or create roles
        guild = interaction.guild
        for role_config in roles_config:
            role = discord.utils.get(guild.roles, name=role_config.role_name)
            
            if not role:
                # Create the role
                try:
                    role = await guild.create_role(
                        name=role_config.role_name,
                        mentionable=True,
                        reason="Created by role bot"
                    )
                    self.logger.info(f"Created role: {role_config.role_name}")
                except Exception as e:
                    self.logger.error(f"Failed to create role {role_config.role_name}: {e}")
                    await interaction.followup.send(
                        f"❌ Failed to create role {role_config.role_name}: {e}",
                        ephemeral=True
                    )
                    return
            
            role_config.role_id = role.id
        
        # Create the embed message
        embed = discord.Embed(
            title="🎭 Role Assignment",
            description="React to this message to get roles!\n\n"
                       "**Available Roles:**",
            color=discord.Color.blue()
        )
        
        for role_config in roles_config:
            role = guild.get_role(role_config.role_id)
            embed.add_field(
                name=f"{role_config.emoji} {role_config.role_name}",
                value=role_config.description,
                inline=False
            )
        
        embed.set_footer(text="Add a reaction to get the role. Remove it to lose the role.")
        
        # Send the message
        try:
            message = await target_channel.send(embed=embed)
            
            # Add reactions
            for role_config in roles_config:
                await message.add_reaction(role_config.emoji)
            
            # Save configuration
            await self.bot.role_manager.set_role_message(
                message.id,
                target_channel.id,
                roles_config
            )
            
            await interaction.followup.send(
                f"✅ Role message created in {target_channel.mention}!",
                ephemeral=True
            )
            
        except Exception as e:
            self.logger.error(f"Failed to create role message: {e}")
            await interaction.followup.send(
                f"❌ Failed to create role message: {e}",
                ephemeral=True
            )
    
    @app_commands.command(name="clear_roles", description="Clear role assignment configuration")
    @app_commands.default_permissions(administrator=True)
    async def clear_roles(self, interaction: discord.Interaction):
        """Clear the role assignment message configuration."""
        await interaction.response.defer(ephemeral=True)
        
        if not await self.bot.role_manager.has_role_message():
            await interaction.followup.send(
                "ℹ️ No role message is currently configured.",
                ephemeral=True
            )
            return
        
        # Get message info before clearing
        role_message = await self.bot.role_manager.get_role_message()
        message_id = role_message.message_id
        
        # Try to delete the message
        try:
            guild = interaction.guild
            channel = guild.get_channel(role_message.channel_id)
            if channel:
                try:
                    message = await channel.fetch_message(message_id)
                    await message.delete()
                    self.logger.info(f"Deleted role message {message_id}")
                except discord.NotFound:
                    self.logger.info(f"Role message {message_id} already deleted")
        except Exception as e:
            self.logger.error(f"Error deleting role message: {e}")
        
        # Clear configuration
        await self.bot.role_manager.clear_role_message()
        
        await interaction.followup.send(
            "✅ Role message configuration cleared.",
            ephemeral=True
        )
    
    @app_commands.command(name="role_status", description="Check role assignment status")
    async def role_status(self, interaction: discord.Interaction):
        """Check the status of role assignments."""
        await interaction.response.defer(ephemeral=True)
        
        if not await self.bot.role_manager.has_role_message():
            await interaction.followup.send(
                "ℹ️ No role message is currently configured.",
                ephemeral=True
            )
            return
        
        role_message = await self.bot.role_manager.get_role_message()
        guild = interaction.guild
        
        embed = discord.Embed(
            title="📊 Role Assignment Status",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Message ID",
            value=str(role_message.message_id),
            inline=False
        )
        
        channel = guild.get_channel(role_message.channel_id)
        if channel:
            embed.add_field(
                name="Channel",
                value=channel.mention,
                inline=False
            )
        
        roles_info = []
        for role_config in role_message.roles:
            role = guild.get_role(role_config.role_id)
            if role:
                member_count = len(role.members)
                roles_info.append(
                    f"{role_config.emoji} **{role_config.role_name}**: {member_count} members"
                )
        
        embed.add_field(
            name="Configured Roles",
            value="\n".join(roles_info) if roles_info else "None",
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(RoleCommands(bot))
