"""
Commands package for the Minecraft Discord Bot

This package contains all bot command implementations organized by functionality.
"""

from .basic_commands import setup_basic_commands
from .location_commands import setup_location_commands

__all__ = ['setup_basic_commands', 'setup_location_commands']
