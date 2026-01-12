#!/usr/bin/env python3
"""
Discord Role Bot - Main Entry Point
Handles role assignment through reactions in a dedicated channel.
"""
import asyncio
import logging
from pathlib import Path
from src.bot.client import RoleBot
from src.utils.config import Config, ConfigError


def setup_logging():
    """Configure application logging."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('bot.log'),
            logging.StreamHandler()
        ]
    )


async def main():
    """Main application entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    bot = None
    try:
        # Load configuration
        config = Config.load()
        logger.info("Configuration loaded successfully")
        
        # Initialize and start bot
        bot = RoleBot(config)
        async with bot:
            await bot.start(config.discord_token)
        
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1
    finally:
        if bot and not bot.is_closed():
            await bot.close()


if __name__ == "__main__":
    try:
        exit(asyncio.run(main()))
    except KeyboardInterrupt:
        pass
