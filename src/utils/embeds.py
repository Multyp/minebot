"""
Discord embed utilities and builders.
"""

import discord
from typing import Optional, List

from ..models.location import Location, LocationInstance


class EmbedBuilder:
    """Helper class for creating consistent Discord embeds."""
    
    FOOTER_TEXT = "🎮 Gooner Status"
    
    @staticmethod
    def create_base_embed(
        title: str, 
        description: Optional[str] = None, 
        color: discord.Color = discord.Color.blue()
    ) -> discord.Embed:
        """Create a base embed with consistent styling."""
        embed = discord.Embed(title=title, description=description, color=color)
        embed.set_footer(text=EmbedBuilder.FOOTER_TEXT)
        return embed
    
    @staticmethod
    def server_status_embed(online: bool, players_online: int = 0, 
                          max_players: int = 0, latency: float = 0.0) -> discord.Embed:
        """Create server status embed."""
        if online:
            embed = EmbedBuilder.create_base_embed(
                title="🟢 Server Status",
                color=discord.Color.green()
            )
            embed.add_field(name="Status", value="✅ Online", inline=True)
            embed.add_field(name="Players", value=f"{players_online}/{max_players}", inline=True)
            embed.add_field(name="Latency", value=f"{latency:.1f}ms", inline=True)
        else:
            embed = EmbedBuilder.create_base_embed(
                title="🔴 Server Status",
                description="❌ Server is offline or unreachable",
                color=discord.Color.red()
            )
        
        return embed
    
    @staticmethod
    def seed_embed(seed: str) -> discord.Embed:
        """Create server seed embed."""
        embed = EmbedBuilder.create_base_embed(
            title="🌱 Server Seed",
            description=f"```{seed}```",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Copy Command",
            value=f"`/seed {seed}`",
            inline=False
        )
        return embed
    
    @staticmethod
    def location_not_found_embed(location_name: str, available_locations: List[str]) -> discord.Embed:
        """Create location not found embed."""
        embed = EmbedBuilder.create_base_embed(
            title="❌ Location Not Found",
            description=f"Location `{location_name}` doesn't exist.",
            color=discord.Color.orange()
        )
        
        if available_locations:
            locations_text = ", ".join([f"`{loc.replace('_', ' ')}`" for loc in available_locations])
        else:
            locations_text = "None"
            
        embed.add_field(
            name="Available Locations",
            value=locations_text,
            inline=False
        )
        return embed
    
    @staticmethod
    def single_location_embed(location: Location, instance_index: int) -> discord.Embed:
        """Create embed for a single location instance."""
        instance = location.get_instance(instance_index)
        
        embed = EmbedBuilder.create_base_embed(
            title="📍 Location Found",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Location",
            value=f"{location.display_name} #{instance_index}",
            inline=False
        )
        
        x, y, z = instance.coordinates
        embed.add_field(name="X", value=f"`{x}`", inline=True)
        embed.add_field(name="Y", value=f"`{y}`", inline=True) 
        embed.add_field(name="Z", value=f"`{z}`", inline=True)
        
        embed.add_field(
            name="Status",
            value=f"{instance.status_emoji} {instance.status_text}",
            inline=True
        )
        
        embed.add_field(
            name="Teleport Command",
            value=f"`{instance.coordinates.teleport_command}`",
            inline=False
        )
        
        return embed
    
    @staticmethod
    def multiple_locations_embed(location: Location) -> discord.Embed:
        """Create embed showing all instances of a location."""
        embed = EmbedBuilder.create_base_embed(
            title="📍 Location Found",
            description=f"**{location.display_name}** - {location.instance_count} instance(s)",
            color=discord.Color.blue()
        )
        
        for i, instance in enumerate(location.instances, 1):
            x, y, z = instance.coordinates
            embed.add_field(
                name=f"#{i} {instance.status_emoji} {instance.status_text}",
                value=f"**Coordinates:** `{instance.coordinates}`\n**Teleport:** `{instance.coordinates.teleport_command}`",
                inline=True
            )
        
        return embed
    
    @staticmethod
    def location_list_embed(locations: List[Location], show_looted: bool = True) -> discord.Embed:
        """Create embed listing all locations."""
        if not locations:
            return EmbedBuilder.create_base_embed(
                title="📍 No Locations",
                description="No locations have been saved yet. Use `/locate add` to create some!",
                color=discord.Color.orange()
            )
        
        embed = EmbedBuilder.create_base_embed(
            title="📍 Saved Locations",
            color=discord.Color.blue()
        )
        
        total_instances = sum(loc.instance_count for loc in locations)
        total_available = sum(loc.available_count for loc in locations)
        total_looted = sum(loc.looted_count for loc in locations)
        
        for location in locations:
            instances_text = []
            
            for i, instance in enumerate(location.instances, 1):
                if instance.looted and not show_looted:
                    continue
                instances_text.append(
                    f"#{i} {instance.status_emoji} `{instance.coordinates}`"
                )
            
            if instances_text:
                embed.add_field(
                    name=f"🏠 {location.display_name} ({location.instance_count})",
                    value="\n".join(instances_text),
                    inline=False
                )
        
        embed.description = (
            f"**{len(locations)}** location types • **{total_instances}** total instances\n"
            f"💎 {total_available} available • 🏴‍☠️ {total_looted} looted"
        )
        
        return embed
    
    @staticmethod
    def location_added_embed(location: Location, instance_index: int) -> discord.Embed:
        """Create embed for successfully added location."""
        instance = location.get_instance(instance_index)
        
        embed = EmbedBuilder.create_base_embed(
            title="✅ Location Added",
            description=f"Successfully added **{location.display_name} #{instance_index}**",
            color=discord.Color.green()
        )
        
        x, y, z = instance.coordinates
        embed.add_field(name="X", value=f"`{x}`", inline=True)
        embed.add_field(name="Y", value=f"`{y}`", inline=True)
        embed.add_field(name="Z", value=f"`{z}`", inline=True)
        
        embed.add_field(
            name="Status",
            value=f"{instance.status_emoji} {instance.status_text}",
            inline=True
        )
        
        embed.add_field(
            name="Teleport Command",
            value=f"`{instance.coordinates.teleport_command}`",
            inline=False
        )
        
        return embed
    
    @staticmethod
    def location_removed_embed(location_name: str, instance_index: Optional[int] = None, 
                             coordinates: Optional[str] = None, instance_count: int = 1) -> discord.Embed:
        """Create embed for successfully removed location."""
        if instance_index is not None:
            title = "✅ Location Instance Removed"
            description = f"Successfully removed **{location_name} #{instance_index}**"
            if coordinates:
                description += f" at `{coordinates}`"
        else:
            title = "✅ Location Removed"
            description = f"Successfully removed **{location_name}** and all {instance_count} instance(s)"
        
        return EmbedBuilder.create_base_embed(
            title=title,
            description=description,
            color=discord.Color.green()
        )
    
    @staticmethod
    def location_status_updated_embed(location: Location, instance_index: int, 
                                    old_looted: bool, new_looted: bool) -> discord.Embed:
        """Create embed for status update."""
        instance = location.get_instance(instance_index)
        instance_text = f" #{instance_index}" if location.instance_count > 1 else ""
        
        embed = EmbedBuilder.create_base_embed(
            title="✅ Status Updated",
            description=f"**{location.display_name}{instance_text}** status changed",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Location",
            value=f"`{instance.coordinates}`",
            inline=False
        )
        
        old_emoji = "🏴‍☠️" if old_looted else "💎"
        old_text = "Looted" if old_looted else "Available"
        
        embed.add_field(
            name="Previous Status",
            value=f"{old_emoji} {old_text}",
            inline=True
        )
        
        embed.add_field(
            name="New Status", 
            value=f"{instance.status_emoji} {instance.status_text}",
            inline=True
        )
        
        return embed
