import discord
from discord import app_commands
from typing import Optional
from location_manager import LocationManager
from embed_utils import EmbedUtils
from minecraft_utils import MinecraftUtils

class LocationCommands:
    """Location management commands"""
    
    def __init__(self, location_manager: LocationManager):
        self.location_manager = location_manager
    
    @app_commands.command(name="get", description="Get coordinates for a specific location")
    @app_commands.describe(
        location="The name of the location to find",
        index="Which instance of the location (1, 2, 3...) - shows all if not specified"
    )
    async def locate_get(self, interaction: discord.Interaction, location: str, index: Optional[int] = None):
        """Get coordinates for a location"""
        location_data = self.location_manager.get_location(location)
        
        if not location_data:
            available_locations = list(self.location_manager.get_all_locations().keys())
            embed = EmbedUtils.create_location_not_found_embed(location, available_locations)
            await interaction.response.send_message(embed=embed)
            return
        
        # Show specific instance
        if index is not None:
            if index < 1 or index > len(location_data):
                embed = EmbedUtils.create_error_embed(
                    title="❌ Invalid Index",
                    message=f"Location `{location}` only has {len(location_data)} instance(s). Use index 1-{len(location_data)}."
                )
                await interaction.response.send_message(embed=embed)
                return
            
            entry = location_data[index - 1]
            embed = EmbedUtils.create_single_location_embed(location, entry, index)
            await interaction.response.send_message(embed=embed)
            return
        
        # Show all instances
        embed = EmbedUtils.create_multiple_locations_embed(location, location_data)
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="list", description="Display all saved locations")
    @app_commands.describe(show_looted="Include looted locations in the list")
    async def locate_list(self, interaction: discord.Interaction, show_looted: bool = True):
        """List all saved locations"""
        locations_data = self.location_manager.get_all_locations()
        embed = EmbedUtils.create_location_list_embed(locations_data, show_looted)
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="add", description="Add a new location instance")
    @app_commands.describe(
        name="Name of the location",
        x="X coordinate",
        y="Y coordinate", 
        z="Z coordinate",
        looted="Whether this location has been looted (default: False)"
    )
    async def locate_add(self, interaction: discord.Interaction, name: str, x: int, y: int, z: int, looted: bool = False):
        """Add a new location"""
        # Validate coordinates
        is_valid, error_msg = MinecraftUtils.validate_coordinates(x, y, z)
        if not is_valid:
            embed = EmbedUtils.create_error_embed(
                title="❌ Invalid Coordinates",
                message=error_msg
            )
            await interaction.response.send_message(embed=embed)
            return
        
        try:
            instance_num, entry = self.location_manager.add_location(name, x, y, z, looted)
            embed = EmbedUtils.create_location_added_embed(name, entry, instance_num)
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            embed = EmbedUtils.create_error_embed(
                title="❌ Error Adding Location",
                message=f"Failed to add location: {str(e)}"
            )
            await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="remove", description="Remove a location instance")
    @app_commands.describe(
        location="Name of the location to remove",
        index="Which instance to remove (1, 2, 3...) - removes all if not specified"
    )
    async def locate_remove(self, interaction: discord.Interaction, location: str, index: Optional[int] = None):
        """Remove a location or specific instance"""
        # Get coordinates for embed if removing specific instance
        coords = None
        if index is not None:
            entry = self.location_manager.get_location_entry(location, index)
            if entry:
                coords = MinecraftUtils.format_coordinates(entry.x, entry.y, entry.z)
        
        success, message, instances_removed = self.location_manager.remove_location(location, index)
        
        if success:
            embed = EmbedUtils.create_location_removed_embed(
                location, instances_removed, index, coords
            )
        else:
            embed = EmbedUtils.create_error_embed(
                title="❌ Remove Failed",
                message=message
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="loot", description="Mark a location as looted or available")
    @app_commands.describe(
        location="Name of the location",
        index="Which instance to update (required if multiple instances exist)",
        looted="True to mark as looted, False to mark as available"
    )
    async def locate_loot(self, interaction: discord.Interaction, location: str, looted: bool, index: Optional[int] = None):
        """Update loot status of a location"""
        success, message, old_status = self.location_manager.update_loot_status(location, looted, index)
        
        if success:
            # Get the updated entry for the embed
            entry = self.location_manager.get_location_entry(location, index or 1)
            if entry:
                embed = EmbedUtils.create_status_updated_embed(location, entry, old_status, index)
            else:
                embed = EmbedUtils.create_embed(
                    title="✅ Status Updated",
                    description=message,
                    color=discord.Color.green()
                )
        else:
            if "Multiple instances" in message:
                embed = EmbedUtils.create_warning_embed(
                    title="⚠️ Multiple Instances Found",
                    message=message
                )
            else:
                embed = EmbedUtils.create_error_embed(
                    title="❌ Update Failed",
                    message=message
                )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="help", description="Show help for all location commands")
    async def locate_help(self, interaction: discord.Interaction):
        """Show comprehensive help for location commands"""
        embed = EmbedUtils.create_embed(
            title="📚 Location Commands Help",
            description="Complete guide to managing server locations",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="📍 `/locate get <location> [index]`",
            value="• Get coordinates for a location\n• Use `index` to get specific instance (1, 2, 3...)\n• Without `index`: shows all instances\n\n**Example:** `/locate get ocean_monument 2`",
            inline=False
        )
        
        embed.add_field(
            name="📋 `/locate list [show_looted]`",
            value="• List all saved locations\n• Set `show_looted: False` to hide looted locations\n• Shows status summary and instance counts\n\n**Example:** `/locate list show_looted:False`",
            inline=False
        )
        
        embed.add_field(
            name="➕ `/locate add <name> <x> <y> <z> [looted]`",
            value="• Add new location instance\n• `looted` defaults to False\n• Creates new location or adds to existing\n\n**Example:** `/locate add stronghold -800 30 1200 looted:False`",
            inline=False
        )
        
        embed.add_field(
            name="❌ `/locate remove <location> [index]`",
            value="• Remove location or specific instance\n• Without `index`: removes entire location\n• With `index`: removes specific instance\n\n**Example:** `/locate remove ocean_monument 3`",
            inline=False
        )
        
        embed.add_field(
            name="🏴‍☠️ `/locate loot <location> <looted> [index]`",
            value="• Mark location as looted or available\n• `looted: True` = 🏴‍☠️ Looted\n• `looted: False` = 💎 Available\n• `index` required for multiple instances\n\n**Example:** `/locate loot stronghold True index:1`",
            inline=False
        )
        
        embed.add_field(
            name="💡 **Tips & Examples**",
            value="• **Multiple instances:** Perfect for ocean monuments, villages, strongholds\n• **Status tracking:** Keep track of what you've looted\n• **Quick teleport:** All responses include `/tp` commands\n• **Instance numbering:** Locations auto-number (#1, #2, #3...)",
            inline=False
        )
        
        embed.add_field(
            name="🎯 **Status Icons**",
            value="💎 **Available** - Ready to explore\n🏴‍☠️ **Looted** - Already explored/raided\n🏠 **Location** - Structure type marker",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

def setup_location_commands(tree: app_commands.CommandTree, location_manager: LocationManager):
    """Setup location commands as a command group"""
    locate_group = app_commands.Group(name="locate", description="Manage server locations")
    location_commands = LocationCommands(location_manager)
    
    # Add all commands to the group
    locate_group.add_command(location_commands.locate_get)
    locate_group.add_command(location_commands.locate_list)
    locate_group.add_command(location_commands.locate_add)
    locate_group.add_command(location_commands.locate_remove)
    locate_group.add_command(location_commands.locate_loot)
    locate_group.add_command(location_commands.locate_help)
    
    # Add the group to the tree
    tree.add_command(locate_group)