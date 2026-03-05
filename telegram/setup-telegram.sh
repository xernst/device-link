#!/usr/bin/env bash
# Set up the Telegram bridge for Device Link.
#
# Usage:
#   bash setup-telegram.sh
#
# This will:
#   1. Install python-telegram-bot
#   2. Prompt for bot token and chat ID
#   3. Install as a LaunchAgent (auto-starts on login)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INSTALL_DIR="$HOME/.device-link/telegram"
PLIST_PATH="$HOME/Library/LaunchAgents/com.device-link.telegram.plist"

echo "==============================="
echo "  Device Link — Telegram Setup"
echo "==============================="
echo ""

# Install python-telegram-bot
echo "Installing python-telegram-bot..."
pip3 install --quiet python-telegram-bot[job-queue] 2>/dev/null || {
    pip3 install --quiet --break-system-packages python-telegram-bot[job-queue]
}
echo "  Done."
echo ""

# Get bot token
echo "Step 1: Create a Telegram bot"
echo "  1. Open Telegram, search for @BotFather"
echo "  2. Send /newbot"
echo "  3. Choose a name (e.g., 'Device Link Swarm')"
echo "  4. Choose a username (e.g., 'device_link_bot')"
echo "  5. Copy the token BotFather gives you"
echo ""
read -rp "Paste your bot token: " BOT_TOKEN
echo ""

# Get chat ID
echo "Step 2: Get your chat ID"
echo "  1. Open Telegram and message your new bot (say 'hello')"
echo "  2. Press Enter here after messaging the bot..."
read -rp ""

CHAT_ID=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/getUpdates" \
    | python3 -c "import json,sys; r=json.load(sys.stdin).get('result',[]); print(r[0]['message']['chat']['id'] if r else '')" 2>/dev/null)

if [[ -z "$CHAT_ID" ]]; then
    echo "  Could not detect chat ID. Make sure you messaged the bot."
    read -rp "  Enter your chat ID manually: " CHAT_ID
fi
echo "  Chat ID: $CHAT_ID"
echo ""

# Install files
mkdir -p "$INSTALL_DIR"
cp "$SCRIPT_DIR/telegram-bridge.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/notify-telegram.sh" "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/notify-telegram.sh"

# Save config
cat > "$INSTALL_DIR/.env" << EOF
TELEGRAM_BOT_TOKEN=$BOT_TOKEN
TELEGRAM_CHAT_ID=$CHAT_ID
EOF
chmod 600 "$INSTALL_DIR/.env"
echo "  Config saved to $INSTALL_DIR/.env"

# Create LaunchAgent
cat > "$PLIST_PATH" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.device-link.telegram</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>${INSTALL_DIR}/telegram-bridge.py</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>TELEGRAM_BOT_TOKEN</key>
        <string>${BOT_TOKEN}</string>
        <key>TELEGRAM_CHAT_ID</key>
        <string>${CHAT_ID}</string>
    </dict>
    <key>KeepAlive</key>
    <true/>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/device-link-telegram.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/device-link-telegram.err</string>
</dict>
</plist>
EOF

echo "  LaunchAgent created: $PLIST_PATH"

# Load the service
launchctl load "$PLIST_PATH" 2>/dev/null || true
echo ""

# Set up bot commands in BotFather
echo "Step 3 (optional): Set bot commands in BotFather"
echo "  Send /setcommands to @BotFather, select your bot, then send:"
echo ""
echo "  status - Swarm health check"
echo "  brief - Daily briefing"
echo "  results - Show recent results"
echo "  help - Show commands"
echo ""

# Test
echo "Testing... sending a message to Telegram."
export TELEGRAM_BOT_TOKEN="$BOT_TOKEN"
export TELEGRAM_CHAT_ID="$CHAT_ID"
bash "$INSTALL_DIR/notify-telegram.sh" "Device Link Telegram bridge is live!"

echo ""
echo "Setup complete! Your bot is running."
echo ""
echo "Usage from Telegram:"
echo "  left: run tests on my-app"
echo "  right: design the auth system"
echo "  /status"
echo "  /brief"
echo ""
echo "Daily brief sent automatically at 8:00 AM."
