#!/bin/bash

TIMESTAMP=$(date +"%Y%m%d%H%M%S")
BACKUP_DIR="/backups/minecraft_$TIMESTAMP"
ZIP_FILE="/backups/minecraft_$TIMESTAMP.zip"
SERVER_SERVICE="minecraft"

# === 1. Save and stop Minecraft ===
echo "Telling Minecraft to flush world data..."
echo "maintenance" > /tmp/mc_maintenance.flag
mcrcon -H 127.0.0.1 -P 25575 -p "your_password" "save-off"
mcrcon -H 127.0.0.1 -P 25575 -p "your_password" "save-all"

echo "Stopping Minecraft server service..."
systemctl stop $SERVER_SERVICE

# === 2. Create temporary backup directory ===
mkdir -p "$BACKUP_DIR"

# Copy server data
rsync -a ./world/ "$BACKUP_DIR/world/"
rsync -a ./mods/ "$BACKUP_DIR/mods/"
rsync -a ./config/ "$BACKUP_DIR/config/"
rsync -a ./server.properties "$BACKUP_DIR/"
rsync -a ./whitelist.json "$BACKUP_DIR/"
rsync -a ./banned-players.json "$BACKUP_DIR/"
rsync -a ./banned-ips.json "$BACKUP_DIR/"
rsync -a ./ops.json "$BACKUP_DIR/"

# === 3. Compress the backup ===
cd /backups
zip -r "$ZIP_FILE" "minecraft_$TIMESTAMP"

# Remove uncompressed folder
rm -rf "$BACKUP_DIR"

# === 4. Upload to Proton Drive ===
rclone copy "$ZIP_FILE" proton:minecraft-backups --progress ## Here I use Proton Drive via rclone, but you can use any cloud service

# === 5. Cleanup local old backups (older than 7 days) ===
find /backups/ -type f -name "*.zip" -mtime +7 -exec rm -f {} \;

# === 6. Restart server ===
echo "Restarting Minecraft server..."
systemctl start $SERVER_SERVICE

# === 7. Re-enable auto saves ===
sleep 100  # give server a moment to start
mcrcon -H 127.0.0.1 -P 25575 -p "your_password" "save-on"

echo "Backup completed, compressed, uploaded, and server restarted."
rm -f /tmp/mc_maintenance.flag
