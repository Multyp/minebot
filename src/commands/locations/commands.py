"""
Location command implementations.
"""

import discord
from discord import app_commands
import logging
from typing import Optional

from ...services.location_manager import LocationManager
from ...models.location import Coordinates
from ...utils.embeds import EmbedBuilder
from ...utils.exceptions import LocationNotFoundError, InvalidLocationIndexError


class LocationCommands:
    """Implements all location-related commands."""
    
    def __init__(self, group: app_commands.Group, location_manager: LocationManager):
        self.group = group
        self.location_manager = location_manager
        self.logger = logging.getLogger(__name__)
        
        self._register_commands()
    
    def _register_commands(self):
        """Register all location commands."""
        
        @self.group.command(name="get", description="Get coordinates for a specific location")
        @app_commands.describe(
            location="The name of the location to find",
            index="Which instance of the location (1, 2, 3...) - shows all if not specified"
        )
        async def get_command(interaction: discord.Interaction, location: str, index: Optional[int] = None):
            await self._handle_get(interaction, location, index)
        
        @self.group.command(name="list", description="Display all saved locations")
        @app_commands.describe(show_looted="Include looted locations in the list")
        async def list_command(interaction: discord.Interaction, show_looted: bool = True):
            await self._handle_list(interaction, show_looted)
        
        @self.group.command(name="add", description="Add a new location instance")
        @app_commands.describe(
            name="Name of the location",
            x="X coordinate",
            y="Y coordinate",
            z="Z coordinate",
            looted="Whether this location has been looted (default: False)"
        )
        async def add_command(interaction: discord.Interaction, name: str, x: int, y: int, z: int, looted: bool = False):
            await self._handle_add(interaction, name, x, y, z, looted)
        
        @self.group.command(name="remove", description="Remove a location instance")
        @app_commands.describe(
            location="Name of the location to remove",
            index="Which instance to remove (1, 2, 3...) - removes all if not specified"
        )
        async def remove_command(interaction: discord.Interaction, location: str, index: Optional[int] = None):
            await self._handle_remove(interaction, location, index)
        
        @self.group.command(name="loot", description="Mark a location as looted or available")
        @app_commands.describe(
            location="Name of the location",
            looted="True to mark as looted, False to mark as available",
            index="Which instance to update (required if multiple instances exist)"
        )
        async def loot_command(interaction: discord.Interaction, location: str, looted: bool, index: Optional[int] = None):
            await self._handle_loot(interaction, location, looted, index)
        
        @self.group.command(name="search", description="Search for locations by name")
        @app_commands.describe(query="Search term to match against location names")
        async def search_command(interaction: discord.Interaction, query: str):
            await self._handle_search(interaction, query)
        
        @self.group.command(name="stats", description="Show location statistics")
        async def stats_command(interaction: discord.Interaction):
            await self._handle_stats(interaction)
        
        @self.group.command(name="available", description="Show only available (unlooted) locations")
        async def available_command(interaction: discord.Interaction):
            await self._handle_available(interaction)
        
        @self.group.command(name="backup", description="Create a backup of location data")
        async def backup_command(interaction: discord.Interaction):
            await self._handle_backup(interaction)
        
        @self.group.command(name="help", description="Show help for all location commands")
        async def help_command(interaction: discord.Interaction):
            await self._handle_help(interaction)
    
    async def _handle_get(self, interaction: discord.Interaction, location_name: str, index: Optional[int]):
        """Handle location get command."""
        try:
            location = await self.location_manager.get_location(location_name)
            
            if index is not None:
                # Show specific instance
                if index < 1 or index > location.instance_count:
                    embed = EmbedBuilder.create_base_embed(
                        title="❌ Invalid Index",
                        description=f"Location `{location_name}` only has {location.instance_count} instance(s). Use index 1-{location.instance_count}.",
                        color=discord.Color.red()
                    )
                    await interaction.response.send_message(embed=embed)
                    return
                
                embed = EmbedBuilder.single_location_embed(location, index)
            else:
                # Show all instances
                embed = EmbedBuilder.multiple_locations_embed(location)
            
            await interaction.response.send_message(embed=embed)
            
        except LocationNotFoundError:
            location_names = await self.location_manager.get_location_names()
            embed = EmbedBuilder.location_not_found_embed(location_name, location_names)
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            self.logger.error(f"Error in get command: {e}")
            await self._send_error_response(interaction, "Failed to retrieve location")
    
    async def _handle_list(self, interaction: discord.Interaction, show_looted: bool):
        """Handle location list command."""
        try:
            locations = await self.location_manager.get_all_locations()
            embed = EmbedBuilder.location_list_embed(locations, show_looted)
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in list command: {e}")
            await self._send_error_response(interaction, "Failed to list locations")
    
    async def _handle_add(self, interaction: discord.Interaction, name: str, x: int, y: int, z: int, looted: bool):
        """Handle location add command."""
        try:
            coordinates = Coordinates(x, y, z)
            instance_index = await self.location_manager.add_location_instance(name, coordinates, looted)
            
            location = await self.location_manager.get_location(name)
            embed = EmbedBuilder.location_added_embed(location, instance_index)
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in add command: {e}")
            await self._send_error_response(interaction, "Failed to add location")
    
    async def _handle_remove(self, interaction: discord.Interaction, location_name: str, index: Optional[int]):
        """Handle location remove command."""
        try:
            removed_instances, remaining_count = await self.location_manager.remove_location_instance(location_name, index)
            
            if index is not None:
                # Removed specific instance
                coordinates_str = str(removed_instances[0].coordinates)
                embed = EmbedBuilder.location_removed_embed(
                    location_name.title(), index, coordinates_str
                )
            else:
                # Removed entire location
                embed = EmbedBuilder.location_removed_embed(
                    location_name.title(), instance_count=len(removed_instances)
                )
            
            await interaction.response.send_message(embed=embed)
            
        except LocationNotFoundError:
            embed = EmbedBuilder.create_base_embed(
                title="❌ Location Not Found",
                description=f"Location `{location_name}` doesn't exist and cannot be removed.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
        except InvalidLocationIndexError as e:
            embed = EmbedBuilder.create_base_embed(
                title="❌ Invalid Index",
                description=str(e),
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            self.logger.error(f"Error in remove command: {e}")
            await self._send_error_response(interaction, "Failed to remove location")
    
    async def _handle_loot(self, interaction: discord.Interaction, location_name: str, looted: bool, index: Optional[int]):
        """Handle location loot status update command."""
        try:
            location = await self.location_manager.get_location(location_name)
            
            # Check if index is required for multiple instances
            if location.instance_count > 1 and index is None:
                embed = EmbedBuilder.create_base_embed(
                    title="⚠️ Multiple Instances Found",
                    description=f"Location `{location_name}` has {location.instance_count} instances. Please specify which one to update using the `index` parameter (1-{location.instance_count}).",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed)
                return
            
            old_status, new_status = await self.location_manager.update_location_status(location_name, looted, index)
            
            # Refresh location data
            location = await self.location_manager.get_location(location_name)
            target_index = index if index is not None else 1
            
            embed = EmbedBuilder.location_status_updated_embed(location, target_index, old_status, new_status)
            await interaction.response.send_message(embed=embed)
            
        except LocationNotFoundError:
            embed = EmbedBuilder.create_base_embed(
                title="❌ Location Not Found",
                description=f"Location `{location_name}` doesn't exist.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
        except InvalidLocationIndexError as e:
            embed = EmbedBuilder.create_base_embed(
                title="❌ Invalid Index",
                description=str(e),
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
        except Exception as e:
            self.logger.error(f"Error in loot command: {e}")
            await self._send_error_response(interaction, "Failed to update location status")
    
    async def _handle_search(self, interaction: discord.Interaction, query: str):
        """Handle location search command."""
        try:
            matching_locations = await self.location_manager.search_locations(query)
            
            if not matching_locations:
                embed = EmbedBuilder.create_base_embed(
                    title="🔍 No Results",
                    description=f"No locations found matching `{query}`.",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed)
                return
            
            embed = EmbedBuilder.create_base_embed(
                title="🔍 Search Results",
                description=f"Found {len(matching_locations)} location(s) matching `{query}`",
                color=discord.Color.blue()
            )
            
            for location in matching_locations[:10]:  # Limit to 10 results
                instances_text = []
                for i, instance in enumerate(location.instances[:3], 1):  # Show first 3 instances
                    instances_text.append(f"#{i} {instance.status_emoji} `{instance.coordinates}`")
                
                if location.instance_count > 3:
                    instances_text.append(f"... and {location.instance_count - 3} more")
                
                embed.add_field(
                    name=f"🏠 {location.display_name} ({location.instance_count})",
                    value="\n".join(instances_text),
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in search command: {e}")
            await self._send_error_response(interaction, "Failed to search locations")
    
    async def _handle_stats(self, interaction: discord.Interaction):
        """Handle location statistics command."""
        try:
            stats = await self.location_manager.get_location_stats()
            
            embed = EmbedBuilder.create_base_embed(
                title="📊 Location Statistics",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="📍 Location Types",
                value=f"`{stats['location_types']}`",
                inline=True
            )
            
            embed.add_field(
                name="🏠 Total Instances",
                value=f"`{stats['total_instances']}`",
                inline=True
            )
            
            embed.add_field(
                name="💎 Available",
                value=f"`{stats['available']}`",
                inline=True
            )
            
            embed.add_field(
                name="🏴‍☠️ Looted",
                value=f"`{stats['looted']}`",
                inline=True
            )
            
            if stats['total_instances'] > 0:
                completion_rate = (stats['looted'] / stats['total_instances']) * 100
                embed.add_field(
                    name="📈 Completion Rate",
                    value=f"`{completion_rate:.1f}%`",
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in stats command: {e}")
            await self._send_error_response(interaction, "Failed to get statistics")
    
    async def _handle_available(self, interaction: discord.Interaction):
        """Handle available locations command."""
        try:
            available_locations = await self.location_manager.get_available_locations()
            
            if not available_locations:
                embed = EmbedBuilder.create_base_embed(
                    title="💎 No Available Locations",
                    description="All locations have been looted! Time to explore and find new ones.",
                    color=discord.Color.orange()
                )
                await interaction.response.send_message(embed=embed)
                return
            
            embed = EmbedBuilder.create_base_embed(
                title="💎 Available Locations",
                description=f"Found {len(available_locations)} location(s) with unlooted instances",
                color=discord.Color.green()
            )
            
            for location in available_locations:
                available_instances = []
                for i, instance in enumerate(location.instances, 1):
                    if not instance.looted:
                        available_instances.append(f"#{i} 💎 `{instance.coordinates}`")
                
                embed.add_field(
                    name=f"🏠 {location.display_name} ({location.available_count}/{location.instance_count} available)",
                    value="\n".join(available_instances[:5]),  # Show first 5
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in available command: {e}")
            await self._send_error_response(interaction, "Failed to get available locations")
    
    async def _handle_backup(self, interaction: discord.Interaction):
        """Handle backup command."""
        try:
            await interaction.response.defer()
            
            success = await self.location_manager.backup_data()
            
            if success:
                embed = EmbedBuilder.create_base_embed(
                    title="✅ Backup Created",
                    description="Location data has been successfully backed up.",
                    color=discord.Color.green()
                )
            else:
                embed = EmbedBuilder.create_base_embed(
                    title="❌ Backup Failed",
                    description="Failed to create backup. Check logs for details.",
                    color=discord.Color.red()
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            self.logger.error(f"Error in backup command: {e}")
            await self._send_error_response(interaction, "Failed to create backup")
    
    async def _handle_help(self, interaction: discord.Interaction):
        """Handle location help command."""
        try:
            embed = EmbedBuilder.create_base_embed(
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
                name="➕ `/locate add <n> <x> <y> <z> [looted]`",
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
                name="🔍 **Additional Commands**",
                value="• `/locate search <query>` - Search locations by name\n• `/locate stats` - Show location statistics\n• `/locate available` - Show only unlooted locations\n• `/locate backup` - Create data backup",
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
            
        except Exception as e:
            self.logger.error(f"Error in help command: {e}")
            await self._send_error_response(interaction, "Failed to show help")
    
    async def _send_error_response(self, interaction: discord.Interaction, message: str):
        """Send error response to user."""
        embed = EmbedBuilder.create_base_embed(
            title="❌ Error",
            description=f"{message}. Please try again later.",
            color=discord.Color.red()
        )
        
        try:
            if interaction.response.is_done():
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, ephemeral=True)
        except:
            pass  # Interaction may have expired
