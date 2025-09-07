#!/usr/bin/env python3
"""
Minecraft Discord Bot - Main Entry Point
Handles application startup and configuration loading.
"""

import asyncio
import logging
from pathlib import Path

from src.bot.client import MinecraftBot
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
    
    try:
        # Load configuration
        config = Config.load()
        logger.info("Configuration loaded successfully")
        
        # Initialize and start bot
        bot = MinecraftBot(config)
        await bot.start()
        
    except ConfigError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except KeyboardInterrupt:
        logger.info("Bot shutdown requested by user")
        return 0
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
