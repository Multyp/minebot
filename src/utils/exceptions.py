"""
Custom exceptions for the bot.
"""


class BotError(Exception):
    """Base exception for bot-related errors."""
    pass


class ConfigError(BotError):
    """Configuration-related errors."""
    pass


# Minecraft-specific server error removed


class LocationError(BotError):
    """Location management errors."""
    pass


class LocationNotFoundError(LocationError):
    """Specific location not found."""
    def __init__(self, location_name: str):
        self.location_name = location_name
        super().__init__(f"Location '{location_name}' not found")


class InvalidLocationIndexError(LocationError):
    """Invalid location instance index."""
    def __init__(self, location_name: str, index: int, max_index: int):
        self.location_name = location_name
        self.index = index
        self.max_index = max_index
        super().__init__(
            f"Invalid index {index} for location '{location_name}'. "
            f"Valid range: 1-{max_index}"
        )


class StorageError(BotError):
    """Data storage and retrieval errors."""
    pass
