# Role & Locations Discord Bot

[![GitHub Pages](https://img.shields.io/badge/GitHub-Pages-blue?logo=github&logoColor=white)](https://multyp.github.io/minebot/)


A modular Discord bot for managing server roles, static locations, and simple automations with a clean, modular architecture.

## Features

- **Role Management**: Simple role assignment and removal commands
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
- Player join/leave notifications posted to a dedicated log channel (if enabled)
- Optional alerting via configured channels

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd minebot
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
ALERT_CHANNEL_ID=123456789012345678  # Channel ID to receive alerts (optional)
LOG_CHANNEL_ID=234567890123456789    # Channel ID for logs (optional)
OWNER_ROLE_ID=456789012345678901    # Role ID used to ping on alerts (optional)

# Data Storage
DATA_DIR=data
```

### Alerts

Set `ALERT_CHANNEL_ID` to a text channel ID to receive automated alerts from the bot (optional). Use `LOG_CHANNEL_ID` to receive activity logs.

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

This bot currently focuses on role and location commands. Server-specific commands have been removed.

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
minebot/
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
