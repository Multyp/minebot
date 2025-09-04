import discord
from typing import Optional, List
from location_manager import LocationEntry

class EmbedUtils:
    """Utility class for creating consistent Discord embeds"""
    
    # Status emojis and text
    STATUS_AVAILABLE_EMOJI = "💎"
    STATUS_LOOTED_EMOJI = "🏴‍☠️"
    LOCATION_EMOJI = "🏠"
    
    @staticmethod
    def create_embed(title: str, description: str = None, color: discord.Color = discord.Color.blue()) -> discord.Embed:
        """Create a consistent embed with bot branding"""
        embed = discord.Embed(title=title, description=description, color=color)
        embed.set_footer(text="🎮 Gooner Status")
        return embed
    
    @staticmethod
    def get_status_emoji(looted: bool) -> str:
        """Get status emoji based on loot status"""
        return EmbedUtils.STATUS_LOOTED_EMOJI if looted else EmbedUtils.STATUS_AVAILABLE_EMOJI
    
    @staticmethod
    def get_status_text(looted: bool) -> str:
        """Get status text based on loot status"""
        return "Looted" if looted else "Available"
    
    @staticmethod
    def create_server_status_embed(is_online: bool, players_online: int = 0, max_players: int = 0, latency: float = 0.0) -> discord.Embed:
        """Create server status embed"""
        if is_online:
            embed = EmbedUtils.create_embed(
                title="🟢 Server Status",
                color=discord.Color.green()
            )
            embed.add_field(name="Status", value="✅ Online", inline=True)
            embed.add_field(name="Players", value=f"{players_online}/{max_players}", inline=True)
            embed.add_field(name="Latency", value=f"{latency:.1f}ms", inline=True)
        else:
            embed = EmbedUtils.create_embed(
                title="🔴 Server Status",
                description="❌ Server is offline or unreachable",
                color=discord.Color.red()
            )
        
        return embed
    
    @staticmethod
    def create_seed_embed(seed: str) -> discord.Embed:
        """Create server seed embed"""
        embed = EmbedUtils.create_embed(
            title="🌱 Server Seed",
            description=f"```{seed}```",
            color=discord.Color.green()
        )
        embed.add_field(name="Copy Command", value=f"`/seed {seed}`", inline=False)
        return embed
    
    @staticmethod
    def create_location_not_found_embed(location: str, available_locations: List[str]) -> discord.Embed:
        """Create embed for location not found error"""
        embed = EmbedUtils.create_embed(
            title="❌ Location Not Found",
            description=f"Location `{location}` doesn't exist.",
            color=discord.Color.orange()
        )
        
        if available_locations:
            locations_text = ", ".join([f"`{loc.replace('_', ' ')}`" for loc in available_locations])
        else:
            locations_text = "None"
        
        embed.add_field(name="Available Locations", value=locations_text, inline=False)
        return embed
    
    @staticmethod
    def create_single_location_embed(location_name: str, entry: LocationEntry, instance_num: Optional[int] = None) -> discord.Embed:
        """Create embed for a single location entry"""
        instance_text = f" #{instance_num}" if instance_num else ""
        
        embed = EmbedUtils.create_embed(
            title="📍 Location Found",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Location",
            value=f"{location_name.replace('_', ' ').title()}{instance_text}",
            inline=False
        )
        embed.add_field(name="X", value=f"`{entry.x}`", inline=True)
        embed.add_field(name="Y", value=f"`{entry.y}`", inline=True)
        embed.add_field(name="Z", value=f"`{entry.z}`", inline=True)
        embed.add_field(
            name="Status",
            value=f"{EmbedUtils.get_status_emoji(entry.looted)} {EmbedUtils.get_status_text(entry.looted)}",
            inline=True
        )
        embed.add_field(
            name="Teleport Command",
            value=f"`/tp {entry.x} {entry.y} {entry.z}`",
            inline=False
        )
        
        return embed
    
    @staticmethod
    def create_multiple_locations_embed(location_name: str, entries: List[LocationEntry]) -> discord.Embed:
        """Create embed for multiple location instances"""
        embed = EmbedUtils.create_embed(
            title="📍 Location Found",
            description=f"**{location_name.replace('_', ' ').title()}** - {len(entries)} instance(s)",
            color=discord.Color.blue()
        )
        
        for i, entry in enumerate(entries, 1):
            embed.add_field(
                name=f"#{i} {EmbedUtils.get_status_emoji(entry.looted)} {EmbedUtils.get_status_text(entry.looted)}",
                value=f"**Coordinates:** `{entry.x}, {entry.y}, {entry.z}`\n**Teleport:** `/tp {entry.x} {entry.y} {entry.z}`",
                inline=True
            )
        
        return embed
    
    @staticmethod
    def create_location_list_embed(locations_data: dict, show_looted: bool = True) -> discord.Embed:
        """Create embed for listing all locations"""
        if not locations_data:
            return EmbedUtils.create_embed(
                title="📍 No Locations",
                description="No locations have been saved yet. Use `/locate add` to create some!",
                color=discord.Color.orange()
            )
        
        embed = EmbedUtils.create_embed(
            title="📍 Saved Locations",
            color=discord.Color.blue()
        )
        
        total_locations = 0
        available_count = 0
        looted_count = 0
        
        for name, location_entries in locations_data.items():
            instances = []
            for i, entry in enumerate(location_entries, 1):
                total_locations += 1
                
                if entry.looted:
                    looted_count += 1
                    if show_looted:
                        instances.append(f"#{i} {EmbedUtils.get_status_emoji(entry.looted)} `{entry.x}, {entry.y}, {entry.z}`")
                else:
                    available_count += 1
                    instances.append(f"#{i} {EmbedUtils.get_status_emoji(entry.looted)} `{entry.x}, {entry.y}, {entry.z}`")
            
            if instances:
                embed.add_field(
                    name=f"{EmbedUtils.LOCATION_EMOJI} {name.replace('_', ' ').title()} ({len(location_entries)})",
                    value="\n".join(instances),
                    inline=False
                )
        
        embed.description = f"**{len(locations_data)}** location types • **{total_locations}** total instances\n💎 {available_count} available • 🏴‍☠️ {looted_count} looted"
        return embed
    
    @staticmethod
    def create_location_added_embed(location_name: str, entry: LocationEntry, instance_num: int) -> discord.Embed:
        """Create embed for successfully added location"""
        embed = EmbedUtils.create_embed(
            title="✅ Location Added",
            description=f"Successfully added **{location_name.title()} #{instance_num}**",
            color=discord.Color.green()
        )
        
        embed.add_field(name="X", value=f"`{entry.x}`", inline=True)
        embed.add_field(name="Y", value=f"`{entry.y}`", inline=True)
        embed.add_field(name="Z", value=f"`{entry.z}`", inline=True)
        embed.add_field(
            name="Status",
            value=f"{EmbedUtils.get_status_emoji(entry.looted)} {EmbedUtils.get_status_text(entry.looted)}",
            inline=True
        )
        embed.add_field(
            name="Teleport Command",
            value=f"`/tp {entry.x} {entry.y} {entry.z}`",
            inline=False
        )
        
        return embed
    
    @staticmethod
    def create_location_removed_embed(location_name: str, instance_count: int, instance_num: Optional[int] = None, coords: Optional[str] = None) -> discord.Embed:
        """Create embed for successfully removed location"""
        if instance_num is not None:
            title = "✅ Location Instance Removed"
            description = f"Successfully removed **{location_name.title()} #{instance_num}**"
            if coords:
                description += f" at `{coords}`"
        else:
            title = "✅ Location Removed"
            description = f"Successfully removed **{location_name.title()}** and all {instance_count} instance(s)"
        
        return EmbedUtils.create_embed(
            title=title,
            description=description,
            color=discord.Color.green()
        )
    
    @staticmethod
    def create_status_updated_embed(location_name: str, entry: LocationEntry, old_status: bool, instance_num: Optional[int] = None) -> discord.Embed:
        """Create embed for updated loot status"""
        instance_text = f" #{instance_num}" if instance_num else ""
        
        embed = EmbedUtils.create_embed(
            title="✅ Status Updated",
            description=f"**{location_name.title()}{instance_text}** status changed",
            color=discord.Color.green()
        )
        
        embed.add_field(
            name="Location",
            value=f"`{entry.x}, {entry.y}, {entry.z}`",
            inline=False
        )
        embed.add_field(
            name="Previous Status",
            value=f"{EmbedUtils.get_status_emoji(old_status)} {EmbedUtils.get_status_text(old_status)}",
            inline=True
        )
        embed.add_field(
            name="New Status",
            value=f"{EmbedUtils.get_status_emoji(entry.looted)} {EmbedUtils.get_status_text(entry.looted)}",
            inline=True
        )
        
        return embed
    
    @staticmethod
    def create_error_embed(title: str, message: str) -> discord.Embed:
        """Create a generic error embed"""
        return EmbedUtils.create_embed(
            title=title,
            description=message,
            color=discord.Color.red()
        )
    
    @staticmethod
    def create_warning_embed(title: str, message: str) -> discord.Embed:
        """Create a generic warning embed"""
        return EmbedUtils.create_embed(
            title=title,
            description=message,
            color=discord.Color.orange()
        )
