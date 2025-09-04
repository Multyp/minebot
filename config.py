import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Configuration class for the Discord bot"""
    
    # Discord Configuration
    TOKEN = os.getenv("DISCORD_TOKEN")
    GUILD_ID = int(os.getenv("GUILD_ID")) if os.getenv("GUILD_ID") else None
    
    # Minecraft Server Configuration
    MC_SERVER_IP = os.getenv("MC_SERVER_IP")
    MC_SERVER_PORT = int(os.getenv("MC_SERVER_PORT")) if os.getenv("MC_SERVER_PORT") else None
    MC_SEED = os.getenv("MC_SEED")
    
    # File Paths
    LOCATIONS_FILE = os.getenv("LOCATIONS_FILE")
    
    @classmethod
    def validate(cls):
        """Validate that all required configuration is present"""
        missing_vars = []
        
        if not cls.TOKEN:
            missing_vars.append("DISCORD_TOKEN")
        if not cls.GUILD_ID:
            missing_vars.append("GUILD_ID")
        if not cls.MC_SERVER_IP:
            missing_vars.append("MC_SERVER_IP")
        if not cls.MC_SERVER_PORT:
            missing_vars.append("MC_SERVER_PORT")
        if not cls.MC_SEED:
            missing_vars.append("MC_SEED")
        if not cls.LOCATIONS_FILE:
            missing_vars.append("LOCATIONS_FILE")
        
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}. "
                f"Please check your .env file and ensure all variables are set."
            )
