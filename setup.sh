#!/usr/bin/env bash
# Device Link — Setup Script
# Run on each helper Mac to configure it as a left-brain or right-brain node.
#
# Usage:
#   ./setup.sh left    # Set up as analytical (left brain) helper
#   ./setup.sh right   # Set up as creative (right brain) helper

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BRAIN="${1:-}"
HOSTNAME_LABEL=""

# --- Validate argument ---
if [[ "$BRAIN" != "left" && "$BRAIN" != "right" ]]; then
    echo "Usage: $0 <left|right>"
    echo ""
    echo "  left   — Analytical brain (code review, testing, debugging, security)"
    echo "  right  — Creative brain (design, research, planning, documentation)"
    exit 1
fi

if [[ "$BRAIN" == "left" ]]; then
    HOSTNAME_LABEL="helper-left"
else
    HOSTNAME_LABEL="helper-right"
fi

echo "======================================"
echo " Device Link Setup — ${BRAIN^^} BRAIN"
echo "======================================"
echo ""

# --- Check macOS ---
if [[ "$(uname)" != "Darwin" ]]; then
    echo "Error: This script is for macOS only." >&2
    exit 1
fi

# --- Install Homebrew if missing ---
if ! command -v brew &>/dev/null; then
    echo "[1/12] Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
else
    echo "[1/12] Homebrew already installed."
fi

# --- Run config scripts ---
echo "[2/12] Installing Tailscale..."
bash "$SCRIPT_DIR/config/tailscale.sh"

echo "[3/12] Installing Ollama + pulling models..."
bash "$SCRIPT_DIR/config/ollama.sh" "$BRAIN"

echo "[4/12] Installing mosh..."
bash "$SCRIPT_DIR/config/mosh.sh"

echo "[5/12] Installing tmux + config..."
bash "$SCRIPT_DIR/config/tmux.sh" "$SCRIPT_DIR/shared/tmux.conf"

echo "[6/12] Configuring Claude Code..."
bash "$SCRIPT_DIR/config/claude-code.sh" "$BRAIN" "$SCRIPT_DIR"

echo "[7/12] Installing/updating OpenClaw gateway..."
bash "$SCRIPT_DIR/config/openclaw.sh" "$BRAIN"

echo "[8/12] Installing Pinchtab browser control..."
bash "$SCRIPT_DIR/config/pinchtab.sh" "$BRAIN"

echo "[9/12] Installing Google Workspace CLI..."
bash "$SCRIPT_DIR/config/gws.sh" "$BRAIN"

echo "[10/12] Installing Python creative tools..."
bash "$SCRIPT_DIR/config/python-tools.sh"

echo "[11/12] Installing JobOps (job hunting automation)..."
bash "$SCRIPT_DIR/config/jobops.sh" "$BRAIN"

# --- Set hostname for easy identification ---
echo "[12/12] Setting hostname to $HOSTNAME_LABEL..."
sudo scutil --set ComputerName "$HOSTNAME_LABEL"
sudo scutil --set LocalHostName "$HOSTNAME_LABEL"

# --- Set up auto-start on login ---
PLIST_DIR="$HOME/Library/LaunchAgents"
PLIST_FILE="$PLIST_DIR/com.device-link.${BRAIN}-brain.plist"
mkdir -p "$PLIST_DIR"

cat > "$PLIST_FILE" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.device-link.${BRAIN}-brain</string>
    <key>ProgramArguments</key>
    <array>
        <string>${SCRIPT_DIR}/${BRAIN}-brain/start.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
    <key>StandardOutPath</key>
    <string>${HOME}/.device-link/${BRAIN}-brain.log</string>
    <key>StandardErrorPath</key>
    <string>${HOME}/.device-link/${BRAIN}-brain.err</string>
</dict>
</plist>
EOF

mkdir -p "$HOME/.device-link"
launchctl load "$PLIST_FILE" 2>/dev/null || true

# --- Install shell aliases ---
echo ""
echo "Installing shell aliases..."
SHELL_RC="$HOME/.zshrc"
if ! grep -q "device-link/shared/aliases.sh" "$SHELL_RC" 2>/dev/null; then
    echo "" >> "$SHELL_RC"
    echo "# Device Link aliases" >> "$SHELL_RC"
    echo "source \"$SCRIPT_DIR/shared/aliases.sh\"" >> "$SHELL_RC"
fi

# --- Summary ---
echo ""
echo "======================================"
echo " Setup Complete — ${BRAIN^^} BRAIN"
echo "======================================"
echo ""
echo "Next steps:"
echo "  1. Run 'tailscale up' and sign in to your Tailscale account"
echo "  2. Note this machine's Tailscale IP: tailscale ip -4"
echo "  3. On your main Mac, add this IP to trigger/trigger.sh"
echo "  4. Start the brain:  ./${BRAIN}-brain/start.sh"
echo "  5. Or reboot — it auto-starts on login"
echo ""
echo "To check status:  tmux ls"
echo "To attach:        tmux attach -t ${BRAIN}-brain"
