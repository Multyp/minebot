import discord
from discord import app_commands
from mcstatus import JavaServer
import json
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
TOKEN = os.getenv("DISCORD_TOKEN")
MC_SERVER_IP = os.getenv("MC_SERVER_IP")
MC_SERVER_PORT = int(os.getenv("MC_SERVER_PORT", 25565))
GUILD_ID = int(os.getenv("GUILD_ID"))
LOCATIONS_FILE = os.getenv("LOCATIONS_FILE", "locations.json")

# Load locations from file
def load_locations():
    if os.path.exists(LOCATIONS_FILE):
        with open(LOCATIONS_FILE, 'r') as f:
            data = json.load(f)
            # Convert old format to new format if needed
            converted_data = {}
            for name, coords in data.items():
                if isinstance(coords, list) and len(coords) == 3 and isinstance(coords[0], int):
                    # Old format: [x, y, z] -> New format: [{"coords": [x, y, z], "looted": false}]
                    converted_data[name] = [{"coords": coords, "looted": False}]
                else:
                    # Already new format
                    converted_data[name] = coords
            return converted_data
    return {"spider_farm": [{"coords": [-135, 106, 408], "looted": False}]}

# Save locations to file
def save_locations():
    with open(LOCATIONS_FILE, 'w') as f:
        json.dump(locations, f, indent=2)

locations = load_locations()

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print(f"Commands synced successfully")

client = MyClient()

# Helper function to create consistent embeds
def create_embed(title: str, description: str = None, color: discord.Color = discord.Color.blue()):
    embed = discord.Embed(title=title, description=description, color=color)
    embed.set_footer(text="🎮 Gooner Status")
    return embed

def get_status_emoji(looted: bool) -> str:
    return "🏴‍☠️" if looted else "💎"

def get_status_text(looted: bool) -> str:
    return "Looted" if looted else "Available"

# Regular commands
@client.tree.command(name="status", description="Check Minecraft server status")
async def status(interaction: discord.Interaction):
    try:
        server = JavaServer.lookup(f"{MC_SERVER_IP}:{MC_SERVER_PORT}")
        status = server.status()
        
        embed = create_embed(
            title="🟢 Server Status",
            color=discord.Color.green()
        )
        embed.add_field(
            name="Status", 
            value="✅ Online", 
            inline=True
        )
        embed.add_field(
            name="Players", 
            value=f"{status.players.online}/{status.players.max}", 
            inline=True
        )
        embed.add_field(
            name="Latency", 
            value=f"{status.latency:.1f}ms", 
            inline=True
        )
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        embed = create_embed(
            title="🔴 Server Status",
            description="❌ Server is offline or unreachable",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)

@client.tree.command(name="seed", description="Get the Minecraft server seed")
async def seed(interaction: discord.Interaction):
    SEED = "-2596841738250690393"
    embed = create_embed(
        title="🌱 Server Seed",
        description=f"```{SEED}```",
        color=discord.Color.green()
    )
    embed.add_field(
        name="Copy Command", 
        value=f"`/seed {SEED}`", 
        inline=False
    )
    await interaction.response.send_message(embed=embed)

# Location command group
locate_group = app_commands.Group(name="locate", description="Manage server locations")

@locate_group.command(name="get", description="Get coordinates for a specific location")
@app_commands.describe(
    location="The name of the location to find",
    index="Which instance of the location (1, 2, 3...) - shows all if not specified"
)
async def locate_get(interaction: discord.Interaction, location: str, index: Optional[int] = None):
    location_key = location.lower().replace(" ", "_")
    
    if location_key not in locations:
        available_locations = ", ".join([f"`{loc.replace('_', ' ')}`" for loc in locations.keys()])
        embed = create_embed(
            title="❌ Location Not Found",
            description=f"Location `{location}` doesn't exist.",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="Available Locations", 
            value=available_locations if available_locations else "None", 
            inline=False
        )
        await interaction.response.send_message(embed=embed)
        return
    
    location_data = locations[location_key]
    
    # If index is specified, show only that instance
    if index is not None:
        if index < 1 or index > len(location_data):
            embed = create_embed(
                title="❌ Invalid Index",
                description=f"Location `{location}` only has {len(location_data)} instance(s). Use index 1-{len(location_data)}.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
            return
        
        entry = location_data[index - 1]
        x, y, z = entry["coords"]
        looted = entry["looted"]
        
        embed = create_embed(
            title="📍 Location Found",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="Location", 
            value=f"{location.replace('_', ' ').title()} #{index}", 
            inline=False
        )
        embed.add_field(name="X", value=f"`{x}`", inline=True)
        embed.add_field(name="Y", value=f"`{y}`", inline=True)
        embed.add_field(name="Z", value=f"`{z}`", inline=True)
        embed.add_field(
            name="Status", 
            value=f"{get_status_emoji(looted)} {get_status_text(looted)}", 
            inline=True
        )
        embed.add_field(
            name="Teleport Command", 
            value=f"`/tp {x} {y} {z}`", 
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)
        return
    
    # Show all instances
    embed = create_embed(
        title="📍 Location Found",
        description=f"**{location.replace('_', ' ').title()}** - {len(location_data)} instance(s)",
        color=discord.Color.blue()
    )
    
    for i, entry in enumerate(location_data, 1):
        x, y, z = entry["coords"]
        looted = entry["looted"]
        
        embed.add_field(
            name=f"#{i} {get_status_emoji(looted)} {get_status_text(looted)}",
            value=f"**Coordinates:** `{x}, {y}, {z}`\n**Teleport:** `/tp {x} {y} {z}`",
            inline=True
        )
    
    await interaction.response.send_message(embed=embed)

@locate_group.command(name="list", description="Display all saved locations")
@app_commands.describe(show_looted="Include looted locations in the list")
async def locate_list(interaction: discord.Interaction, show_looted: bool = True):
    if not locations:
        embed = create_embed(
            title="📍 No Locations",
            description="No locations have been saved yet. Use `/locate add` to create some!",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)
        return
    
    embed = create_embed(
        title="📍 Saved Locations",
        color=discord.Color.blue()
    )
    
    total_locations = 0
    available_count = 0
    looted_count = 0
    
    for name, location_data in locations.items():
        instances = []
        for i, entry in enumerate(location_data, 1):
            x, y, z = entry["coords"]
            looted = entry["looted"]
            total_locations += 1
            
            if looted:
                looted_count += 1
                if show_looted:
                    instances.append(f"#{i} {get_status_emoji(looted)} `{x}, {y}, {z}`")
            else:
                available_count += 1
                instances.append(f"#{i} {get_status_emoji(looted)} `{x}, {y}, {z}`")
        
        if instances:  # Only show if there are instances to display
            embed.add_field(
                name=f"🏠 {name.replace('_', ' ').title()} ({len(location_data)})",
                value="\n".join(instances) if instances else "No instances to show",
                inline=False
            )
    
    embed.description = f"**{len(locations)}** location types • **{total_locations}** total instances\n💎 {available_count} available • 🏴‍☠️ {looted_count} looted"
    await interaction.response.send_message(embed=embed)

@locate_group.command(name="add", description="Add a new location instance")
@app_commands.describe(
    name="Name of the location",
    x="X coordinate",
    y="Y coordinate", 
    z="Z coordinate",
    looted="Whether this location has been looted (default: False)"
)
async def locate_add(interaction: discord.Interaction, name: str, x: int, y: int, z: int, looted: bool = False):
    location_key = name.lower().replace(" ", "_")
    
    new_entry = {"coords": [x, y, z], "looted": looted}
    
    if location_key in locations:
        locations[location_key].append(new_entry)
        instance_num = len(locations[location_key])
    else:
        locations[location_key] = [new_entry]
        instance_num = 1
    
    save_locations()
    
    embed = create_embed(
        title="✅ Location Added",
        description=f"Successfully added **{name.title()} #{instance_num}**",
        color=discord.Color.green()
    )
    embed.add_field(name="X", value=f"`{x}`", inline=True)
    embed.add_field(name="Y", value=f"`{y}`", inline=True)
    embed.add_field(name="Z", value=f"`{z}`", inline=True)
    embed.add_field(
        name="Status", 
        value=f"{get_status_emoji(looted)} {get_status_text(looted)}", 
        inline=True
    )
    embed.add_field(
        name="Teleport Command", 
        value=f"`/tp {x} {y} {z}`", 
        inline=False
    )
    
    await interaction.response.send_message(embed=embed)

@locate_group.command(name="remove", description="Remove a location instance")
@app_commands.describe(
    location="Name of the location to remove",
    index="Which instance to remove (1, 2, 3...) - removes all if not specified"
)
async def locate_remove(interaction: discord.Interaction, location: str, index: Optional[int] = None):
    location_key = location.lower().replace(" ", "_")
    
    if location_key not in locations:
        embed = create_embed(
            title="❌ Location Not Found",
            description=f"Location `{location}` doesn't exist and cannot be removed.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
        return
    
    if index is not None:
        # Remove specific instance
        if index < 1 or index > len(locations[location_key]):
            embed = create_embed(
                title="❌ Invalid Index",
                description=f"Location `{location}` only has {len(locations[location_key])} instance(s). Use index 1-{len(locations[location_key])}.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
            return
        
        removed_entry = locations[location_key].pop(index - 1)
        
        # If no instances left, remove the entire location
        if not locations[location_key]:
            del locations[location_key]
        
        save_locations()
        
        x, y, z = removed_entry["coords"]
        embed = create_embed(
            title="✅ Location Instance Removed",
            description=f"Successfully removed **{location.title()} #{index}** at `{x}, {y}, {z}`",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    else:
        # Remove entire location
        instance_count = len(locations[location_key])
        del locations[location_key]
        save_locations()
        
        embed = create_embed(
            title="✅ Location Removed",
            description=f"Successfully removed **{location.title()}** and all {instance_count} instance(s)",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

@locate_group.command(name="loot", description="Mark a location as looted or available")
@app_commands.describe(
    location="Name of the location",
    index="Which instance to update (required if multiple instances exist)",
    looted="True to mark as looted, False to mark as available"
)
async def locate_loot(interaction: discord.Interaction, location: str, looted: bool, index: Optional[int] = None):
    location_key = location.lower().replace(" ", "_")
    
    if location_key not in locations:
        embed = create_embed(
            title="❌ Location Not Found",
            description=f"Location `{location}` doesn't exist.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
        return
    
    location_data = locations[location_key]
    
    # If multiple instances exist and no index specified, require index
    if len(location_data) > 1 and index is None:
        embed = create_embed(
            title="⚠️ Multiple Instances Found",
            description=f"Location `{location}` has {len(location_data)} instances. Please specify which one to update using the `index` parameter (1-{len(location_data)}).",
            color=discord.Color.orange()
        )
        await interaction.response.send_message(embed=embed)
        return
    
    # Determine which instance to update
    if index is None:
        target_index = 0  # Single instance
    else:
        if index < 1 or index > len(location_data):
            embed = create_embed(
                title="❌ Invalid Index",
                description=f"Location `{location}` only has {len(location_data)} instance(s). Use index 1-{len(location_data)}.",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed)
            return
        target_index = index - 1
    
    # Update the looted status
    old_status = location_data[target_index]["looted"]
    location_data[target_index]["looted"] = looted
    save_locations()
    
    x, y, z = location_data[target_index]["coords"]
    instance_text = f" #{index}" if index is not None else ""
    
    embed = create_embed(
        title="✅ Status Updated",
        description=f"**{location.title()}{instance_text}** status changed",
        color=discord.Color.green()
    )
    embed.add_field(
        name="Location", 
        value=f"`{x}, {y}, {z}`", 
        inline=False
    )
    embed.add_field(
        name="Previous Status", 
        value=f"{get_status_emoji(old_status)} {get_status_text(old_status)}", 
        inline=True
    )
    embed.add_field(
        name="New Status", 
        value=f"{get_status_emoji(looted)} {get_status_text(looted)}", 
        inline=True
    )
    
    await interaction.response.send_message(embed=embed)

@locate_group.command(name="help", description="Show help for all location commands")
async def locate_help(interaction: discord.Interaction):
    embed = create_embed(
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
        name="➕ `/locate add <name> <x> <y> <z> [looted]`",
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

# Add the group to the tree
client.tree.add_command(locate_group)

@client.event
async def on_ready():
    print(f'🤖 Bot is ready! Logged in as {client.user}')
    print(f'🌐 Connected to {len(client.guilds)} guilds')
    
    total_instances = sum(len(instances) for instances in locations.values())
    print(f'📍 Loaded {len(locations)} location types with {total_instances} total instances')

if __name__ == "__main__":
    client.run(TOKEN)