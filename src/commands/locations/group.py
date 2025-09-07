"""
Location command group management.
"""

import discord
from discord import app_commands

from ...services.location_manager import LocationManager
from .commands import LocationCommands


class LocationCommandGroup:
    """Manages the location command group and its subcommands."""
    
    def __init__(self, tree: app_commands.CommandTree, location_manager: LocationManager):
        self.tree = tree
        self.location_manager = location_manager
        
        # Create command group
        self.group = app_commands.Group(
            name="locate",
            description="Manage server locations"
        )
        
        # Initialize command handlers
        self.commands = LocationCommands(self.group, location_manager)
        
        # Add group to tree
        self.tree.add_command(self.group)
