#!/usr/bin/env bash
# Device Link — Install & configure Pinchtab browser control on a helper Mac.
# Gives AI agents full browser control via HTTP API.
#
# Usage:
#   bash config/pinchtab.sh <left|right>

set -euo pipefail

BRAIN="${1:-}"
if [[ -z "$BRAIN" ]]; then
    echo "Usage: bash config/pinchtab.sh <left|right>" >&2
    exit 1
fi

echo ""
echo "=== Pinchtab Browser Control — ${BRAIN} brain ==="
echo ""

PINCHTAB_DIR="$HOME/.pinchtab"
PINCHTAB_PORT="${PINCHTAB_PORT:-9867}"

# Bind to Tailscale IP only — never expose on all interfaces
TAILSCALE_IP=$(tailscale ip -4 2>/dev/null || echo "127.0.0.1")

# --- Install ---

if command -v pinchtab &>/dev/null; then
    CURRENT_VER=$(pinchtab --version 2>/dev/null | head -1 || echo "unknown")
    echo "Pinchtab already installed: $CURRENT_VER"
    echo "Updating..."
else
    echo "Installing Pinchtab..."
fi

curl -fsSL https://pinchtab.com/install.sh | bash

echo "Installed: $(pinchtab --version 2>/dev/null || echo 'ok')"

# --- Generate auth token ---

mkdir -p "$PINCHTAB_DIR"
chmod 700 "$PINCHTAB_DIR"

TOKEN_FILE="$PINCHTAB_DIR/token"
if [[ -f "$TOKEN_FILE" ]]; then
    PINCHTAB_TOKEN=$(cat "$TOKEN_FILE")
    echo "Using existing auth token"
else
    PINCHTAB_TOKEN=$(openssl rand -hex 32)
    echo "$PINCHTAB_TOKEN" > "$TOKEN_FILE"
    chmod 600 "$TOKEN_FILE"
    echo "Generated new auth token → $TOKEN_FILE"
fi

# --- Configure for headless agent use ---

ENV_FILE="$PINCHTAB_DIR/env"
cat > "$ENV_FILE" <<EOF
# Pinchtab configuration for ${BRAIN} brain
BRIDGE_PORT=${PINCHTAB_PORT}
BRIDGE_TOKEN=${PINCHTAB_TOKEN}
BRIDGE_HEADLESS=true
BRIDGE_STEALTH=full
BRIDGE_BLOCK_IMAGES=true
BRIDGE_NO_ANIMATIONS=true
BRIDGE_BIND=${TAILSCALE_IP}
BRIDGE_PROFILE=${PINCHTAB_DIR}/chrome-profile
BRIDGE_STATE_DIR=${PINCHTAB_DIR}
BRIDGE_MAX_TABS=10
EOF
chmod 600 "$ENV_FILE"
echo "Config written → $ENV_FILE"

# --- LaunchAgent for auto-start ---

PLIST_FILE="$HOME/Library/LaunchAgents/com.pinchtab.agent.plist"
mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST_FILE" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.pinchtab.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>$(command -v pinchtab)</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>BRIDGE_PORT</key>
        <string>${PINCHTAB_PORT}</string>
        <key>BRIDGE_TOKEN</key>
        <string>${PINCHTAB_TOKEN}</string>
        <key>BRIDGE_HEADLESS</key>
        <string>true</string>
        <key>BRIDGE_STEALTH</key>
        <string>full</string>
        <key>BRIDGE_BLOCK_IMAGES</key>
        <string>true</string>
        <key>BRIDGE_NO_ANIMATIONS</key>
        <string>true</string>
        <key>BRIDGE_BIND</key>
        <string>${TAILSCALE_IP}</string>
        <key>BRIDGE_PROFILE</key>
        <string>${PINCHTAB_DIR}/chrome-profile</string>
        <key>BRIDGE_STATE_DIR</key>
        <string>${PINCHTAB_DIR}</string>
        <key>BRIDGE_MAX_TABS</key>
        <string>10</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>${HOME}/.device-link/pinchtab.log</string>
    <key>StandardErrorPath</key>
    <string>${HOME}/.device-link/pinchtab.err</string>
</dict>
</plist>
EOF

launchctl unload "$PLIST_FILE" 2>/dev/null || true
launchctl load "$PLIST_FILE"

echo "LaunchAgent installed — Pinchtab starts on boot"

# --- Verify ---

sleep 2
if curl -s -o /dev/null -w '%{http_code}' "http://localhost:${PINCHTAB_PORT}/health" -H "Authorization: Bearer ${PINCHTAB_TOKEN}" | grep -q "200"; then
    echo "Pinchtab is running on port ${PINCHTAB_PORT}"
else
    echo "Warning: Pinchtab health check failed — may need a moment to start" >&2
fi

echo ""
echo "=== Pinchtab Ready ==="
echo "  Port:    ${PINCHTAB_PORT}"
echo "  Token:   ${TOKEN_FILE}"
echo "  Profile: ${PINCHTAB_DIR}/chrome-profile"
echo "  Logs:    ~/.device-link/pinchtab.log"
echo ""
echo "  Test:  curl -s http://localhost:${PINCHTAB_PORT}/health -H 'Authorization: Bearer \$(cat ${TOKEN_FILE})'"
echo "  Text:  curl -s http://localhost:${PINCHTAB_PORT}/text -H 'Authorization: Bearer \$(cat ${TOKEN_FILE})'"
echo ""
