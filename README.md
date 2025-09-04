# Minecraft Discord Bot

A Discord bot for managing Minecraft server status and location tracking with a clean, modular architecture.

## Features

- 🟢 **Server Status**: Check if your Minecraft server is online
- 🌱 **Server Seed**: Display and copy the world seed
- 📍 **Location Management**: Add, remove, and track multiple instances of locations
- 🏴‍☠️ **Loot Tracking**: Mark locations as looted or available
- 💎 **Multi-Instance Support**: Handle multiple instances of the same structure type
- 🎮 **Rich Embeds**: Beautiful Discord embeds with consistent branding

## Project Structure

```
minebot/
├── bot.py                      # Main bot entry point
├── config.py                   # Configuration management
├── location_manager.py         # Location data management
├── minecraft_utils.py          # Minecraft server utilities
├── embed_utils.py             # Discord embed utilities
├── commands/
│   ├── __init__.py
│   ├── basic_commands.py      # Status and seed commands
│   └── location_commands.py   # Location management commands
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── .env                      # Your environment variables (create from .env.example)
├── locations.json            # Location data storage
└── README.md                 # This file
```

## Installation

1. **Clone or download the project files**

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your actual values
   ```

4. **Configure your Discord bot:**
   - Create a Discord application and bot at https://discord.com/developers/applications
   - Copy the bot token to your `.env` file
   - Invite the bot to your server with appropriate permissions

## Configuration

Edit your `.env` file with the following values:

- `DISCORD_TOKEN`: Your Discord bot token
- `GUILD_ID`: Your Discord server ID
- `MC_SERVER_IP`: Your Minecraft server IP address
- `MC_SERVER_PORT`: Your Minecraft server port (default: 25565)
- `MC_SEED`: Your Minecraft world seed
- `LOCATIONS_FILE`: Location data file path (default: locations.json)

## Usage

### Running the Bot

```bash
python bot.py
```

### Available Commands

#### Basic Commands
- `/status` - Check Minecraft server status
- `/seed` - Display the server seed

#### Location Management (`/locate`)
- `/locate get <location> [index]` - Get coordinates for a location
- `/locate list [show_looted]` - List all saved locations
- `/locate add <name> <x> <y> <z> [looted]` - Add a new location
- `/locate remove <location> [index]` - Remove a location or instance
- `/locate loot <location> <looted> [index]` - Update loot status
- `/locate help` - Show detailed help for location commands

### Example Usage

```
# Add a new stronghold location
/locate add stronghold -800 30 1200

# Add multiple ocean monuments
/locate add ocean_monument 1200 60 -400
/locate add ocean_monument -800 62 800
/locate add ocean_monument 400 58 1600

# Get all ocean monuments
/locate get ocean_monument

# Get specific instance
/locate get ocean_monument 2

# Mark a location as looted
/locate loot stronghold True

# List only available (unlooted) locations
/locate list show_looted:False
```

## Architecture Overview

### Modular Design
The bot follows a clean, modular architecture with separation of concerns:

- **`config.py`**: Centralized configuration management with environment variable support
- **`location_manager.py`**: Data layer for location storage and management with backward compatibility
- **`minecraft_utils.py`**: Minecraft-specific utilities and server communication
- **`embed_utils.py`**: Discord embed creation with consistent styling
- **`commands/`**: Command definitions organized by functionality

### Key Features

1. **Type Safety**: Uses dataclasses and type hints for better code reliability
2. **Error Handling**: Comprehensive error handling with user-friendly messages
3. **Data Validation**: Validates coordinates and handles edge cases
4. **Backward Compatibility**: Automatically migrates old data formats
5. **Extensible**: Easy to add new commands and features
6. **Environment-Based Config**: Secure token management through environment variables

### Location Data Structure

Locations are stored with the following structure:
```json
{
  "location_name": [
    {
      "coords": [x, y, z],
      "looted": false
    }
  ]
}
```

This allows for multiple instances of the same location type (e.g., multiple ocean monuments).

## Development

### Adding New Commands

1. Create command methods in the appropriate command file
2. Use the existing embed utilities for consistent styling
3. Handle errors gracefully with user-friendly messages
4. Add the command to the setup function

### Code Style

- Use type hints for better code documentation
- Follow Python naming conventions
- Use dataclasses for structured data
- Handle exceptions appropriately
- Add docstrings to public methods

## Contributing

1. Follow the existing code structure and patterns
2. Add appropriate error handling
3. Use the embed utilities for consistent Discord responses
4. Test commands thoroughly before submitting

## License

This project is open source and available under the MIT License.
