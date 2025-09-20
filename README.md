# Minecraft Discord Bot

[![GitHub Pages](https://img.shields.io/badge/GitHub-Pages-blue?logo=github&logoColor=white)](https://multyp.github.io/minebot/)


A feature-rich Discord bot for managing Minecraft server information and locations with a clean, modular architecture.

## Features

- **Server Status**: Check Minecraft server status, player count, and latency
 - **Player Activity Logging**: Monitor player join/leave events and post them to a configured log channel
 - **Advancement Monitoring**: Remote SSH-based watcher that posts Minecraft advancement completions to a Discord channel
 - **Maintenance Detection**: Detect maintenance mode via a remote flag file (/tmp/mc_maintenance.flag) and post maintenance notices instead of crash alerts
- **Location Management**: Store, track, and manage coordinates for various locations
- **Loot Tracking**: Mark locations as looted or available
- **Multiple Instances**: Support multiple instances of the same location type
- **Rich Embeds**: Beautiful Discord embeds with consistent styling
- **Event-Driven Architecture**: Decoupled components with IPC communication

## Architecture Overview

```
📁 src/
├── 🤖 bot/          # Main bot client and events
├── ⚡ commands/     # Discord command handlers  
├── 🔧 services/     # Business logic services
├── 📊 models/       # Data models
├── 🛠️  utils/       # Utilities and helpers
└── 📡 ipc/         # Inter-process communication
```

### Key Components

- **Component Architecture**: Clean separation of concerns with single-responsibility modules
- **Event Bus System**: Decoupled communication between services using events
- **Service Layer**: Business logic separated from Discord interactions
- **Data Models**: Structured data representation with validation
- **Storage Service**: Async file I/O with atomic operations

Additional runtime features:
- Remote advancement monitoring via SSH (reads player advancement JSON files and posts to Discord)
- Player join/leave notifications posted to a dedicated log channel
- Crash detection with recovery alerts and optional role pings

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd minecraft-discord-bot
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Set up Discord bot:**
   - Create a bot at https://discord.com/developers/applications
   - Get the bot token and add to `.env`
   - Invite bot to your server with appropriate permissions

## Configuration

Edit the `.env` file with your settings:

```env
# Discord Configuration
DISCORD_TOKEN=your_discord_bot_token_here
DISCORD_GUILD_ID=your_guild_id_here_optional
ALERT_CHANNEL_ID=123456789012345678  # Channel ID to receive crash/recovery alerts (optional)
LOG_CHANNEL_ID=234567890123456789    # Channel ID to receive player join/leave logs (optional)
ADVANCEMENTS_CHANNEL_ID=345678901234567890  # Channel ID for advancement notifications (optional)
OWNER_ROLE_ID=456789012345678901    # Role ID used to ping on alerts (optional)

# Minecraft Server Configuration  
MC_SERVER_HOST=your.minecraft.server.ip
MC_SERVER_PORT=25565
MC_WORLD_DIR=/home/minecraft/server/world  # remote world path for advancement monitoring
MC_SERVER_DIR=/home/minecraft/server      # remote server directory (contains whitelist.json)

# Server Information
MC_SEED=your_server_seed_here

# Remote server SSH credentials (required for advancement monitoring)
SERVER_HOST=your.remote.server.ip
SERVER_USER=ssh_user
SERVER_PASSWORD=ssh_password

# Data Storage
DATA_DIR=data
```

### Crash / Recovery Alerts

Set `ALERT_CHANNEL_ID` to a text channel ID to receive automatic alerts when the Minecraft server becomes unreachable for ~2 minutes (4 failed checks at 30s intervals) and a recovery notice when it comes back online. If unset, alerts are skipped. Use `LOG_CHANNEL_ID` to receive player join/leave notifications. Advancement monitoring posts to `ADVANCEMENTS_CHANNEL_ID` when enabled and properly configured.

## Running the Bot

```bash
python main.py
```

## Static Locations Viewer (GitHub Pages)

This repository also publishes a static web viewer for the location data to **GitHub Pages** (served from the `static/` + `data/` directories).

### How it works

- GitHub Action workflow (`.github/workflows/deploy-pages.yml`) runs on each push to `main`.
- It copies everything from `static/` into a temporary `dist/` directory root.
- It copies `data/locations.json` to `dist/data/locations.json` so the page can fetch it with `fetch('./data/locations.json')`.
- The site is then deployed via the official `actions/deploy-pages` action.

### Enabling Pages (first time)
1. Go to Repository Settings → Pages.
2. Set Source to: GitHub Actions.
3. Save.

### Viewing Locally

You can open `static/index.html` directly or serve it (recommended so the cache-busting query works consistently):

```bash
python -m http.server -d static 8080
# Then open http://localhost:8080
```

Ensure `data/locations.json` is reachable at `http://localhost:8080/data/locations.json` (you may need to copy the `data` folder under `static` for local ad‑hoc serving):

```bash
cp -R data static/
```

### Updating Data

Any commit that changes `data/locations.json` will redeploy automatically. The client adds a cache-busting `?_=<timestamp>` query parameter.

### Custom Domains / Project Pages

If this is a project page served at `https://<user>.github.io/<repo>/`, relative links (`./data/locations.json` and `./mc-background.png`) continue to work without modification.


## Commands

### Server Commands

- `/status` - Check Minecraft server status
- `/seed` - Get the server seed

### Location Commands

- `/locate get <location> [index]` - Get coordinates for a location
- `/locate list [show_looted]` - List all saved locations
- `/locate add <name> <x> <y> <z> [looted]` - Add new location
- `/locate remove <location> [index]` - Remove location(s)
- `/locate loot <location> <looted> [index]` - Update loot status
- `/locate help` - Show detailed command help

## Development

### Project Structure

```
minecraft-discord-bot/
├── src/
│   ├── bot/
│   │   ├── client.py              # Main bot client
│   │   └── events.py              # Event handlers
│   ├── commands/
│   │   ├── server.py              # Server commands
│   │   └── locations/             # Location commands
│   │       ├── group.py           # Command group
│   │       └── commands.py        # Individual commands
│   ├── services/
│   │   ├── location_manager.py    # Location management
│   │   ├── minecraft.py           # Server integration
│   │   └── storage.py             # File I/O
│   ├── models/
│   │   └── location.py            # Data models
│   ├── utils/
│   │   ├── config.py              # Configuration
│   │   ├── embeds.py              # Discord embeds
│   │   └── exceptions.py          # Custom exceptions
│   └── ipc/
│       └── events.py              # Event bus system
├── data/                          # Persistent storage
├── config/                        # Configuration files
└── main.py                        # Entry point
```

### Adding New Commands

1. Create command handler in appropriate module
2. Register with command tree or group
3. Add embed builders if needed
4. Emit events for component communication

### Event System

The bot uses an event-driven architecture for component communication:

```python
# Subscribe to events
event_bus.subscribe('location_added', handler)

# Emit events
event_bus.emit('location_added', data)
```

### Error Handling

- Custom exception hierarchy for different error types
- Graceful error responses to users
- Comprehensive logging for debugging

## Data Storage

Location data is stored in JSON format with the following structure:

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

The bot automatically handles legacy format migration and creates backups.

## Contributing

1. Follow the established architecture patterns
2. Add tests for new features
3. Update documentation
4. Use descriptive commit messages
