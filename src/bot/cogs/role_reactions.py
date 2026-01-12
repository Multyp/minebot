"""
Handler for role assignment through reactions.
"""
import discord
from discord.ext import commands
import logging


class RoleReactions(commands.Cog):
    """Handles reaction events for role assignments."""
    
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        """Handle when a user adds a reaction."""
        # Ignore bot reactions
        if payload.user_id == self.bot.user.id:
            return
        
        # Check if this is the role message
        role_message = await self.bot.role_manager.get_role_message()
        if not role_message or payload.message_id != role_message.message_id:
            return
        
        # Get the role configuration for this emoji
        emoji_str = str(payload.emoji)
        role_config = await self.bot.role_manager.get_role_by_emoji(emoji_str)
        
        if not role_config:
            self.logger.warning(f"Unknown emoji {emoji_str} used on role message")
            return
        
        # Get guild and member
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        
        member = guild.get_member(payload.user_id)
        if not member:
            return
        
        # Get role
        role = guild.get_role(role_config.role_id)
        if not role:
            self.logger.error(f"Role {role_config.role_name} not found")
            return
        
        # Check if member already has role
        if role in member.roles:
            self.logger.debug(f"{member.name} already has role {role.name}")
            return
        
        # Add role
        try:
            await member.add_roles(role, reason="Role reaction")
            self.logger.info(f"✅ Added role {role.name} to {member.name}")
            
            # Emit event
            self.bot.event_bus.emit('role_assigned', {
                'user_id': member.id,
                'user_name': str(member),
                'role_id': role.id,
                'role_name': role.name
            })
            
            # Try to send DM
            try:
                await member.send(
                    f"✅ You've been given the **{role.name}** role in {guild.name}!"
                )
            except discord.Forbidden:
                # User has DMs disabled
                pass
            
        except discord.Forbidden:
            self.logger.error(f"Missing permissions to add role {role.name}")
        except Exception as e:
            self.logger.error(f"Error adding role {role.name} to {member.name}: {e}")
    
    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """Handle when a user removes a reaction."""
        # Ignore bot reactions
        if payload.user_id == self.bot.user.id:
            return
        
        # Check if this is the role message
        role_message = await self.bot.role_manager.get_role_message()
        if not role_message or payload.message_id != role_message.message_id:
            return
        
        # Get the role configuration for this emoji
        emoji_str = str(payload.emoji)
        role_config = await self.bot.role_manager.get_role_by_emoji(emoji_str)
        
        if not role_config:
            return
        
        # Get guild and member
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return
        
        member = guild.get_member(payload.user_id)
        if not member:
            return
        
        # Get role
        role = guild.get_role(role_config.role_id)
        if not role:
            self.logger.error(f"Role {role_config.role_name} not found")
            return
        
        # Check if member has role
        if role not in member.roles:
            self.logger.debug(f"{member.name} doesn't have role {role.name}")
            return
        
        # Remove role
        try:
            await member.remove_roles(role, reason="Role reaction removed")
            self.logger.info(f"❌ Removed role {role.name} from {member.name}")
            
            # Emit event
            self.bot.event_bus.emit('role_removed', {
                'user_id': member.id,
                'user_name': str(member),
                'role_id': role.id,
                'role_name': role.name
            })
            
            # Try to send DM
            try:
                await member.send(
                    f"❌ The **{role.name}** role has been removed in {guild.name}."
                )
            except discord.Forbidden:
                # User has DMs disabled
                pass
            
        except discord.Forbidden:
            self.logger.error(f"Missing permissions to remove role {role.name}")
        except Exception as e:
            self.logger.error(f"Error removing role {role.name} from {member.name}: {e}")


async def setup(bot):
    await bot.add_cog(RoleReactions(bot))
