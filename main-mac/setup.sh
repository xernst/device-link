#!/usr/bin/env bash
# Device Link — Main Mac Setup
# One-shot installer for the main Mac (the portable one).
#
# This sets up:
#   1. Tailscale (mesh networking)
#   2. mosh (resilient SSH)
#   3. device-link CLI on PATH
#   4. Shell aliases
#   5. Slash commands for Claude Code
#   6. Config file with defaults
#   7. Mission Control dashboard (optional)
#   8. Telegram bridge (optional)
#
# Usage:
#   bash main-mac/setup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "======================================"
echo " Device Link — Main Mac Setup"
echo "======================================"
echo ""

# --- Check macOS ---
if [[ "$(uname)" != "Darwin" ]]; then
    echo "Error: This script is for macOS only." >&2
    exit 1
fi

# --- Homebrew ---
if ! command -v brew &>/dev/null; then
    echo "[1/8] Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    eval "$(/opt/homebrew/bin/brew shellenv)"
else
    echo "[1/8] Homebrew already installed."
fi

# --- Tailscale ---
echo "[2/8] Installing Tailscale..."
if ! command -v tailscale &>/dev/null; then
    brew install --cask tailscale
    echo "  Installed. Run 'tailscale up' to connect."
else
    echo "  Already installed."
fi

# --- mosh ---
echo "[3/8] Installing mosh..."
if ! command -v mosh &>/dev/null; then
    brew install mosh
else
    echo "  Already installed."
fi

# --- device-link CLI on PATH ---
echo "[4/8] Installing device-link CLI..."
LINK_TARGET="/usr/local/bin/device-link"
if [[ -L "$LINK_TARGET" ]] || [[ -f "$LINK_TARGET" ]]; then
    echo "  Updating existing symlink."
    sudo ln -sf "$SCRIPT_DIR/trigger/trigger.sh" "$LINK_TARGET"
else
    sudo mkdir -p /usr/local/bin
    sudo ln -sf "$SCRIPT_DIR/trigger/trigger.sh" "$LINK_TARGET"
fi
sudo chmod +x "$LINK_TARGET"
echo "  device-link is now on PATH."

# --- Shell aliases ---
echo "[5/8] Installing shell aliases..."
SHELL_RC="$HOME/.zshrc"
if ! grep -q "device-link/shared/aliases.sh" "$SHELL_RC" 2>/dev/null; then
    echo "" >> "$SHELL_RC"
    echo "# Device Link aliases" >> "$SHELL_RC"
    echo "source \"$SCRIPT_DIR/shared/aliases.sh\"" >> "$SHELL_RC"
    echo "  Added to $SHELL_RC"
else
    echo "  Already in $SHELL_RC"
fi

# --- Slash commands ---
echo "[6/8] Installing Claude Code slash commands..."
CMD_DIR="$HOME/.claude/commands"
mkdir -p "$CMD_DIR"

COMMANDS=(left-brain right-brain both-brains swarm-status swarm-results daily-brief)
for cmd in "${COMMANDS[@]}"; do
    if [[ -f "$SCRIPT_DIR/main-mac/commands/${cmd}.md" ]]; then
        cp "$SCRIPT_DIR/main-mac/commands/${cmd}.md" "$CMD_DIR/${cmd}.md"
    fi
done

# Also install from existing commands if they exist at the expected paths
for cmd_file in "$CMD_DIR"/*.md; do
    [[ -f "$cmd_file" ]] && break
done
echo "  Installed ${#COMMANDS[@]} slash commands."

# --- Config file ---
echo "[7/8] Setting up configuration..."
CONFIG_DIR="$HOME/.device-link"
CONFIG_FILE="$CONFIG_DIR/config"
mkdir -p "$CONFIG_DIR/results"

if [[ ! -f "$CONFIG_FILE" ]]; then
    cp "$SCRIPT_DIR/shared/config.example" "$CONFIG_FILE"
    echo "  Created $CONFIG_FILE (edit with your Tailscale hostnames)"
else
    echo "  Config already exists at $CONFIG_FILE"
fi

# --- Optional: Mission Control ---
echo "[8/8] Optional components..."
echo ""
read -rp "  Install Mission Control dashboard? [y/N] " INSTALL_MC
if [[ "$INSTALL_MC" =~ ^[Yy] ]]; then
    bash "$SCRIPT_DIR/main-mac/setup-mission-control.sh"
fi

echo ""
read -rp "  Set up Telegram bridge? [y/N] " INSTALL_TG
if [[ "$INSTALL_TG" =~ ^[Yy] ]]; then
    bash "$SCRIPT_DIR/telegram/setup-telegram.sh"
fi

# --- Summary ---
echo ""
echo "======================================"
echo " Main Mac Setup Complete"
echo "======================================"
echo ""
echo "Quick start:"
echo "  device-link status                    # check helper health"
echo "  device-link left \"run tests\"          # send to left brain"
echo "  device-link right \"design auth\"       # send to right brain"
echo "  device-link both \"review PR\"          # send to both"
echo "  device-link pull                      # sync results from helpers"
echo "  device-link attach left               # reconnect to left brain tmux"
echo ""
echo "Slash commands (in Claude Code):"
echo "  /left-brain <task>"
echo "  /right-brain <task>"
echo "  /both-brains <task>"
echo "  /swarm-status"
echo "  /daily-brief"
echo ""
echo "Next steps:"
echo "  1. Edit ~/.device-link/config with your Tailscale hostnames"
echo "  2. Run 'tailscale up' if not already connected"
echo "  3. Try: device-link status"
